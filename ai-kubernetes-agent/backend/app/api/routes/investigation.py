from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from loguru import logger

from app.ai.agent import AIKubernetesAgent, get_ai_agent
from app.ai.llm_client import LLMClientError
from app.models.auth import AuthContext
from app.models.investigation import InvestigationRequest, InvestigationResponse
from app.services.clusters import ClusterContextService, get_cluster_context_service
from app.services.insforge import InvestigationRunStore, get_run_store, require_auth_context
from app.services.investigation import InvestigationService, get_investigation_service

router = APIRouter(tags=["investigation"])


@router.post("/investigate", response_model=InvestigationResponse)
async def investigate_cluster(
    service: Annotated[InvestigationService, Depends(get_investigation_service)],
    ai_agent: Annotated[AIKubernetesAgent, Depends(get_ai_agent)],
    auth: Annotated[AuthContext, Depends(require_auth_context)],
    run_store: Annotated[InvestigationRunStore, Depends(get_run_store)],
    cluster_contexts: Annotated[ClusterContextService, Depends(get_cluster_context_service)],
    request: InvestigationRequest | None = None,
) -> InvestigationResponse:
    request = request or InvestigationRequest()
    run_id = request.investigation_id or uuid4()

    if request.context:
        available = await run_in_threadpool(cluster_contexts.list_contexts)
        if available.error:
            raise HTTPException(
                status_code=503,
                detail={
                    "message": "Unable to read Kubernetes clusters from the kubeconfig.",
                    "guidance": ["Mount a readable kubeconfig into the backend container."],
                },
            )
        if request.context not in available.contexts:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "The selected Kubernetes cluster is no longer available.",
                    "guidance": ["Refresh the cluster list and choose an available cluster."],
                },
            )
        service = service.for_context(request.context)

    if request.investigation_id:
        await run_in_threadpool(run_store.ensure_owned, run_id)
    else:
        await run_in_threadpool(run_store.create, run_id, auth.user_id, request.namespace)

    def publish_progress(step: str) -> None:
        run_store.update(run_id, status="running", current_step=step)

    try:
        investigation = await run_in_threadpool(service.investigate, publish_progress)
        errors = _collect_errors(investigation)
        usable_evidence = _has_usable_evidence(investigation)
        cluster_healthy = usable_evidence and not _has_problem_findings(investigation) and not errors
        diagnosis = None

        if usable_evidence and not cluster_healthy:
            await run_in_threadpool(run_store.update, run_id, status="running", current_step="ai_reasoning")
            try:
                diagnosis = await ai_agent.diagnose(investigation)
            except LLMClientError as exc:
                errors.append(f"ai: {exc}")
        elif not usable_evidence:
            errors.append("No Kubernetes evidence could be collected")

        final_status = "success" if cluster_healthy or (diagnosis and not errors) else "partial"
        message, guidance = _friendly_outcome(errors, cluster_healthy)
        final_root_cause = diagnosis.root_cause if diagnosis else message if cluster_healthy else None
        await run_in_threadpool(
            run_store.update,
            run_id,
            status="completed" if final_status == "success" else "partial",
            current_step="root_cause_found" if diagnosis or cluster_healthy else "failed",
            root_cause=final_root_cause,
            confidence=diagnosis.confidence if diagnosis else 100 if cluster_healthy else None,
        )

        return InvestigationResponse(
            investigation_id=run_id,
            status=final_status,
            investigation=investigation,
            diagnosis=diagnosis,
            errors=errors,
            message=message,
            guidance=guidance,
            cluster_healthy=cluster_healthy,
        )
    except Exception as exc:
        logger.exception("Investigation {} failed unexpectedly", run_id)
        try:
            await run_in_threadpool(
                run_store.update, run_id, status="failed", current_step="failed"
            )
        except Exception:
            logger.exception("Could not mark investigation {} as failed", run_id)
        raise HTTPException(
            status_code=500,
            detail={
                "message": "The investigation could not be completed.",
                "guidance": ["Try again. If the problem continues, check the backend logs."],
            },
        ) from exc


def _collect_errors(investigation: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for section_name, section in investigation.items():
        if section.get("error"):
            errors.append(f"{section_name}: {section['error']}")
        for error in section.get("errors", []):
            errors.append(f"{section_name}: {error}")
    return list(dict.fromkeys(errors))


def _has_usable_evidence(investigation: dict[str, Any]) -> bool:
    return any(
        [
            investigation.get("pods", {}).get("total_pods", 0) > 0,
            bool(investigation.get("pods", {}).get("problematic_pods")),
            bool(investigation.get("logs", {}).get("findings")),
            bool(investigation.get("events", {}).get("findings")),
            investigation.get("deployments", {}).get("total_deployments", 0) > 0,
            bool(investigation.get("deployments", {}).get("unhealthy_deployments")),
            investigation.get("network", {}).get("total_services", 0) > 0,
            bool(investigation.get("network", {}).get("issues")),
        ]
    )


def _has_problem_findings(investigation: dict[str, Any]) -> bool:
    return any(
        [
            bool(investigation.get("pods", {}).get("problematic_pods")),
            bool(investigation.get("logs", {}).get("findings")),
            bool(investigation.get("events", {}).get("findings")),
            bool(investigation.get("deployments", {}).get("unhealthy_deployments")),
            bool(investigation.get("network", {}).get("issues")),
        ]
    )


def _friendly_outcome(errors: list[str], cluster_healthy: bool) -> tuple[str | None, list[str]]:
    if cluster_healthy:
        return "No critical Kubernetes issues detected. Cluster appears healthy.", []
    combined = " ".join(errors).lower()
    if "kubeconfig" in combined or "current-context" in combined or "no such file" in combined:
        return (
            "Unable to read the Kubernetes configuration.",
            ["Verify the kubeconfig path.", "Mount the kubeconfig into the backend container."],
        )
    if any(token in combined for token in ["connection refused", "unable to connect", "i/o timeout"]):
        return (
            "Unable to connect to the Kubernetes cluster.",
            ["Verify that the cluster is running.", "Check kubeconfig access and the API server address."],
        )
    if "forbidden" in combined or "unauthorized" in combined:
        return (
            "Kubernetes denied access to one or more resources.",
            ["Verify the current user's kubectl permissions.", "Grant read access to pods, logs, events, deployments, services, and endpoints."],
        )
    if "ai:" in combined:
        return (
            "Cluster evidence was collected, but AI reasoning is temporarily unavailable.",
            ["Verify the OpenRouter key and model.", "Try the investigation again shortly."],
        )
    if errors:
        return (
            "The investigation completed with incomplete Kubernetes evidence.",
            ["Check cluster access and retry the investigation."],
        )
    return None, []
