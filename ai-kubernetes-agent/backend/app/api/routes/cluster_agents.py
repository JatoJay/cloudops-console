from datetime import UTC, datetime
import shlex
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect

from app.core.config import Settings, get_settings
from app.models.auth import AuthContext
from app.models.cluster_agent import (
    AgentPairRequest, AgentPairResponse, ClusterJob, ClusterJobRequest,
    CloudConnectionsResponse, CloudProject, ConnectedCluster,
    PairingTokenRequest, PairingTokenResponse,
)
from app.services.cluster_agents import AgentAdminStore, ClusterAgentStore, agent_connections
from app.services.insforge import require_auth_context

router = APIRouter(prefix="/api", tags=["cluster-agents"])


def user_store(auth: AuthContext, settings: Settings) -> ClusterAgentStore:
    return ClusterAgentStore(settings.insforge_url, auth.access_token, settings.insforge_timeout_seconds)


def admin_store(settings: Settings) -> AgentAdminStore:
    return AgentAdminStore(settings.insforge_url, settings.insforge_api_key, settings.insforge_timeout_seconds)


@router.post("/cluster-connections/pairing-token", response_model=PairingTokenResponse)
async def create_pairing_token(
    request: PairingTokenRequest,
    auth: Annotated[AuthContext, Depends(require_auth_context)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PairingTokenResponse:
    token, expires_at = await user_store(auth, settings).create_pairing_token(
        auth.user_id, request.cluster_name, request.provider
    )
    control_plane = settings.public_api_url.rstrip("/")
    helm_token = shlex.quote(f"pairingToken={token}")
    helm_url = shlex.quote(f"controlPlaneUrl={control_plane}")
    helm_name = shlex.quote(f"clusterName={request.cluster_name}")
    if request.provider == "gcp":
        cli_command = (
            "git clone --depth 1 https://github.com/JatoJay/cloudops-console.git "
            "cloudops-console && cd cloudops-console/ai-kubernetes-agent/backend && "
            "python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && "
            f".venv/bin/python -m app.cloud_agent --control-plane {shlex.quote(control_plane)} "
            f"--token {shlex.quote(token)} --connection-name {shlex.quote(request.cluster_name)}"
        )
        helm_command = ""
    else:
        cli_command = (f"cloudops-agent --control-plane {shlex.quote(control_plane)} "
                       f"--token {shlex.quote(token)} --cluster-name {shlex.quote(request.cluster_name)}")
        helm_command = (f"helm upgrade --install cloudops-agent ./helm/cloudops-agent "
                        f"--namespace cloudops-agent --create-namespace "
                        f"--set-string {helm_token} --set-string {helm_url} --set-string {helm_name}")
    return PairingTokenResponse(
        token=token,
        expires_at=expires_at,
        helm_command=helm_command,
        cli_command=cli_command,
    )


@router.get("/remote-clusters", response_model=list[ConnectedCluster])
async def list_remote_clusters(auth: Annotated[AuthContext, Depends(require_auth_context)], settings: Annotated[Settings, Depends(get_settings)]):
    return await user_store(auth, settings).list_clusters("kubernetes")


@router.get("/cloud-connections", response_model=CloudConnectionsResponse)
async def list_cloud_connections(
    auth: Annotated[AuthContext, Depends(require_auth_context)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CloudConnectionsResponse:
    connections = await user_store(auth, settings).list_clusters("gcp")
    projects = []
    for connection in connections:
        for project in connection.get("metadata", {}).get("projects", []):
            projects.append(CloudProject(
                connection_id=connection["id"],
                project_id=str(project.get("project_id", "")),
                display_name=str(project.get("display_name") or project.get("project_id", "")),
                lifecycle_state=str(project.get("lifecycle_state", "ACTIVE")),
            ))
    return CloudConnectionsResponse(connections=connections, projects=projects)


@router.delete("/remote-clusters/{cluster_id}", status_code=204)
async def revoke_remote_cluster(cluster_id: UUID, auth: Annotated[AuthContext, Depends(require_auth_context)], settings: Annotated[Settings, Depends(get_settings)]):
    await user_store(auth, settings).delete_cluster(cluster_id)


@router.post("/remote-clusters/{cluster_id}/jobs", response_model=ClusterJob)
async def create_cluster_job(cluster_id: UUID, request: ClusterJobRequest, auth: Annotated[AuthContext, Depends(require_auth_context)], settings: Annotated[Settings, Depends(get_settings)]):
    job = await user_store(auth, settings).create_job(auth.user_id, cluster_id, request.job_type, request.payload)
    await agent_connections.dispatch(job)
    return job


@router.get("/remote-clusters/{cluster_id}/jobs", response_model=list[ClusterJob])
async def list_cluster_jobs(cluster_id: UUID, auth: Annotated[AuthContext, Depends(require_auth_context)], settings: Annotated[Settings, Depends(get_settings)]):
    return await user_store(auth, settings).list_jobs(cluster_id)


@router.post("/agents/pair", response_model=AgentPairResponse)
async def pair_agent(request: AgentPairRequest, settings: Annotated[Settings, Depends(get_settings)]):
    cluster_id = await admin_store(settings).pair(request.token, request.cluster_name, request.provider)
    return AgentPairResponse(cluster_id=cluster_id)


@router.websocket("/ws/agent/{cluster_id}")
async def agent_socket(websocket: WebSocket, cluster_id: UUID, settings: Annotated[Settings, Depends(get_settings)]):
    protocols = [part.strip() for part in websocket.headers.get("sec-websocket-protocol", "").split(",")]
    token = protocols[1] if len(protocols) == 2 and protocols[0] == "agent" else ""
    store = admin_store(settings)
    try:
        if not token or not await store.authenticate_agent(cluster_id, token):
            await websocket.close(code=1008, reason="Invalid agent credential")
            return
        await agent_connections.connect(cluster_id, websocket)
        await store.mark_cluster(cluster_id, "online")
        for job in await store.queued_jobs(cluster_id):
            await agent_connections.dispatch(job)
        while True:
            message = await websocket.receive_json()
            kind = message.get("type")
            if kind == "heartbeat":
                await store.mark_cluster(cluster_id, "online")
                await websocket.send_json({"type": "heartbeat_ack"})
                continue
            if kind == "projects":
                projects = message.get("projects")
                if isinstance(projects, list):
                    await store.update_metadata(cluster_id, {"projects": projects[:500]})
                continue
            try:
                job_id = UUID(message["job_id"])
            except (KeyError, ValueError):
                continue
            if kind == "progress":
                await store.append_progress(job_id, str(message.get("message", "Working"))[:500])
            elif kind == "result":
                result = message.get("result") or {}
                await store.update_job(job_id, status="completed", result=result, completed_at=datetime.now(UTC).isoformat())
                agent_connections.resolve_result(job_id, result)
            elif kind == "failed":
                error = str(message.get("error", "Agent job failed"))[:2000]
                await store.update_job(job_id, status="failed", error=error, completed_at=datetime.now(UTC).isoformat())
                agent_connections.reject_result(job_id, error)
    except WebSocketDisconnect:
        pass
    finally:
        agent_connections.disconnect(cluster_id)
        try:
            await store.mark_cluster(cluster_id, "offline")
        except HTTPException:
            pass
