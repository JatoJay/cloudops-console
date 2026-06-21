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

router = APIRouter(prefix="/api", tags=["cost-analysis"])
progress_router = APIRouter(tags=["cost-analysis-progress"])


@router.post("/analyze", response_model=CostAnalysisResponse)
async def analyze_cloud_costs(
    scanner: Annotated[CloudScanner, Depends(get_cloud_scanner)],
    analyzer: Annotated[AIAnalyzer, Depends(get_ai_analyzer)],
    auth: Annotated[AuthContext, Depends(require_auth_context)],
    store: Annotated[AnalysisStore, Depends(get_analysis_store)],
    request: AnalyzeRequest | None = None,
) -> CostAnalysisResponse:
    """Scan cloud resources first, then produce a structured AI cost analysis."""
    request = request or AnalyzeRequest()
    await progress_broker.publish(request.analysis_id, "Fetching resource groups...")
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
    scanner: Annotated[CloudScanner, Depends(get_cloud_scanner)],
    _: Annotated[AuthContext, Depends(require_auth_context)],
) -> dict[str, list[str]]:
    try:
        resource_groups = await run_in_threadpool(scanner.resource_groups)
    except CloudScannerError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"resource_groups": resource_groups}


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
