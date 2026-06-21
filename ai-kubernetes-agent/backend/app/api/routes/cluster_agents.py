from datetime import UTC, datetime
import shlex
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect

from app.core.config import Settings, get_settings
from app.models.auth import AuthContext
from app.models.cluster_agent import (
    AgentPairRequest, AgentPairResponse, ClusterJob, ClusterJobRequest,
    ConnectedCluster, PairingTokenRequest, PairingTokenResponse,
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
    token, expires_at = await user_store(auth, settings).create_pairing_token(auth.user_id, request.cluster_name)
    control_plane = settings.public_api_url.rstrip("/")
    helm_token = shlex.quote(f"pairingToken={token}")
    helm_url = shlex.quote(f"controlPlaneUrl={control_plane}")
    helm_name = shlex.quote(f"clusterName={request.cluster_name}")
    return PairingTokenResponse(
        token=token,
        expires_at=expires_at,
        helm_command=(f"helm upgrade --install cloudops-agent ./helm/cloudops-agent "
                      f"--namespace cloudops-agent --create-namespace "
                      f"--set-string {helm_token} --set-string {helm_url} --set-string {helm_name}"),
        cli_command=(f"cloudops-agent --control-plane {shlex.quote(control_plane)} "
                     f"--token {shlex.quote(token)} --cluster-name {shlex.quote(request.cluster_name)}"),
    )


@router.get("/remote-clusters", response_model=list[ConnectedCluster])
async def list_remote_clusters(auth: Annotated[AuthContext, Depends(require_auth_context)], settings: Annotated[Settings, Depends(get_settings)]):
    return await user_store(auth, settings).list_clusters()


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
    cluster_id = await admin_store(settings).pair(request.token, request.cluster_name)
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
            try:
                job_id = UUID(message["job_id"])
            except (KeyError, ValueError):
                continue
            if kind == "progress":
                await store.append_progress(job_id, str(message.get("message", "Working"))[:500])
            elif kind == "result":
                await store.update_job(job_id, status="completed", result=message.get("result") or {}, completed_at=datetime.now(UTC).isoformat())
            elif kind == "failed":
                await store.update_job(job_id, status="failed", error=str(message.get("error", "Agent job failed"))[:2000], completed_at=datetime.now(UTC).isoformat())
    except WebSocketDisconnect:
        pass
    finally:
        agent_connections.disconnect(cluster_id)
        try:
            await store.mark_cluster(cluster_id, "offline")
        except HTTPException:
            pass
