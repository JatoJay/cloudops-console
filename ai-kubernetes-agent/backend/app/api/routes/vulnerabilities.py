from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.core.config import Settings, get_settings
from app.kubernetes.vulnerability_scanner import VulnerabilityScanner, VulnerabilityScannerError
from app.models.auth import AuthContext
from app.models.vulnerability import VulnerabilityScanRequest, VulnerabilityScanResponse
from app.services.clusters import ClusterContextService, get_cluster_context_service
from app.services.insforge import require_auth_context

router = APIRouter(prefix="/api", tags=["kubernetes-security"])


def get_vulnerability_scanner(settings: Settings = Depends(get_settings)) -> VulnerabilityScanner:
    return VulnerabilityScanner(
        kubeconfig_path=settings.kubeconfig_path,
        timeout_seconds=settings.vulnerability_scan_timeout_seconds,
    )


@router.post("/vulnerability-scan", response_model=VulnerabilityScanResponse)
async def scan_kubernetes_vulnerabilities(
    request: VulnerabilityScanRequest,
    _: Annotated[AuthContext, Depends(require_auth_context)],
    scanner: Annotated[VulnerabilityScanner, Depends(get_vulnerability_scanner)],
    clusters: Annotated[ClusterContextService, Depends(get_cluster_context_service)],
) -> VulnerabilityScanResponse:
    available = await run_in_threadpool(clusters.list_contexts)
    if available.error:
        raise HTTPException(status_code=503, detail="Unable to read Kubernetes clusters")
    if request.context not in available.contexts:
        raise HTTPException(status_code=400, detail="The selected Kubernetes cluster is unavailable")
    try:
        return await run_in_threadpool(scanner.scan, request.context)
    except VulnerabilityScannerError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
