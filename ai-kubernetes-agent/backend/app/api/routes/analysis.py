import asyncio
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from pydantic import ValidationError

from app.ai.llm_client import LLMClientError
from app.ai_analyzer import AIAnalyzer, get_ai_analyzer
from app.cloud_scanner import CloudScanner, CloudScannerError, get_cloud_scanner
from app.models.auth import AuthContext
from app.models.cost_analysis import (
    AnalysisHistoryItem,
    AnalyzeRequest,
    CostAnalysisResponse,
)
from app.services.analyses import AnalysisStore, get_analysis_store
from app.services.insforge import require_auth_context, require_websocket_auth
from app.services.progress import progress_broker
from app.services.cluster_agents import ClusterAgentStore, agent_connections, get_cluster_agent_store

router = APIRouter(prefix="/api", tags=["cost-analysis"])
progress_router = APIRouter(tags=["cost-analysis-progress"])


@router.post("/analyze", response_model=CostAnalysisResponse)
async def analyze_cloud_costs(
    scanner: Annotated[CloudScanner, Depends(get_cloud_scanner)],
    analyzer: Annotated[AIAnalyzer, Depends(get_ai_analyzer)],
    auth: Annotated[AuthContext, Depends(require_auth_context)],
    store: Annotated[AnalysisStore, Depends(get_analysis_store)],
    agent_store: Annotated[ClusterAgentStore, Depends(get_cluster_agent_store)],
    request: AnalyzeRequest | None = None,
) -> CostAnalysisResponse:
    """Scan cloud resources first, then produce a structured AI cost analysis."""
    request = request or AnalyzeRequest()
    await progress_broker.publish(request.analysis_id, "Fetching cloud projects...")
    if request.connection_id:
        if not request.project_id:
            raise HTTPException(status_code=422, detail="Select a connected Google Cloud project")
        connection = await agent_store.get_connection(request.connection_id, "gcp")
        if connection["status"] != "online":
            raise HTTPException(status_code=409, detail="The Google Cloud connector is offline")
        available_projects = {
            item.get("project_id") for item in connection.get("metadata", {}).get("projects", [])
        }
        if request.project_id not in available_projects:
            raise HTTPException(status_code=403, detail="The selected project is not available through this connector")
        resource_groups = [request.project_id]
        await progress_broker.publish(
            request.analysis_id, f"Scanning resources in {request.project_id}..."
        )
        job = await agent_store.create_job(
            auth.user_id,
            request.connection_id,
            "cloud_cost_analysis",
            {"project_id": request.project_id, "analysis_id": str(request.analysis_id)},
        )
        job_id = UUID(job["id"])
        result_future = agent_connections.expect_result(job_id)
        if not await agent_connections.dispatch(job):
            agent_connections.forget_result(job_id)
            raise HTTPException(status_code=409, detail="The Google Cloud connector disconnected")
        try:
            result = await asyncio.wait_for(result_future, timeout=180)
        except TimeoutError as exc:
            agent_connections.forget_result(job_id)
            raise HTTPException(status_code=504, detail="The Google Cloud inventory scan timed out") from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        raw_resources = result.get("resources")
        if not isinstance(raw_resources, list):
            raise HTTPException(status_code=502, detail="The cloud connector returned invalid inventory")
        resources = [item for item in raw_resources if isinstance(item, dict)]
    else:
        try:
            resource_groups = (
                [request.resource_group]
                if request.resource_group
                else await run_in_threadpool(scanner.resource_groups)
            )
            resources = []
            for resource_group in resource_groups:
                await progress_broker.publish(
                    request.analysis_id, f"Scanning resources in {resource_group}..."
                )
                resources.extend(await run_in_threadpool(scanner.scan, resource_group))
        except CloudScannerError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    try:
        await progress_broker.publish(request.analysis_id, "Analyzing costs with AI...")
        analysis = await analyzer.analyze(resources)
    except (LLMClientError, ValidationError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    await progress_broker.publish(request.analysis_id, "Storing results...")
    await run_in_threadpool(
        store.create_completed,
        request.analysis_id,
        auth.user_id,
        ", ".join(resource_groups),
        len(resources),
        analysis,
    )
    await progress_broker.publish(request.analysis_id, "Analysis complete")
    return CostAnalysisResponse(analysis_id=request.analysis_id, **analysis.model_dump())


@router.get("/history", response_model=list[AnalysisHistoryItem])
async def get_analysis_history(
    store: Annotated[AnalysisStore, Depends(get_analysis_store)],
) -> list[AnalysisHistoryItem]:
    return await run_in_threadpool(store.list_for_user)


@router.get("/resource-groups")
async def get_resource_groups(
    auth: Annotated[AuthContext, Depends(require_auth_context)],
    agent_store: Annotated[ClusterAgentStore, Depends(get_cluster_agent_store)],
) -> dict[str, list]:
    del auth
    connections = await agent_store.list_clusters("gcp")
    projects = []
    for connection in connections:
        for project in connection.get("metadata", {}).get("projects", []):
            if project.get("project_id"):
                projects.append({
                    "connection_id": connection["id"],
                    "project_id": project["project_id"],
                    "display_name": project.get("display_name") or project["project_id"],
                    "status": connection["status"],
                })
    return {"resource_groups": [item["project_id"] for item in projects], "projects": projects}


@progress_router.websocket("/ws/progress/{analysis_id}")
async def analysis_progress(
    websocket: WebSocket,
    analysis_id: UUID,
    _: Annotated[AuthContext, Depends(require_websocket_auth)],
) -> None:
    await websocket.accept(subprotocol="bearer")
    try:
        async with progress_broker.subscribe(analysis_id) as queue:
            while True:
                message = await queue.get()
                await websocket.send_text(message)
                if message == "Analysis complete":
                    await websocket.close(code=1000)
                    return
    except WebSocketDisconnect:
        return
