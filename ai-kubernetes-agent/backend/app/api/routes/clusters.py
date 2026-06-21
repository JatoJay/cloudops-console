from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool

from app.models.auth import AuthContext
from app.services.clusters import ClusterContextService, get_cluster_context_service
from app.services.insforge import require_auth_context

router = APIRouter(tags=["clusters"])


@router.get("/clusters")
async def list_clusters(
    _auth: Annotated[AuthContext, Depends(require_auth_context)],
    service: Annotated[ClusterContextService, Depends(get_cluster_context_service)],
) -> dict[str, object]:
    result = await run_in_threadpool(service.list_contexts)
    if result.error:
        return {
            "status": "unavailable",
            "contexts": [],
            "current_context": None,
            "message": "No Kubernetes clusters are available to the backend.",
            "guidance": [
                "Mount your kubeconfig into the backend container.",
                "Verify that kubectl can read the kubeconfig file.",
            ],
        }
    return {
        "status": "success",
        "contexts": result.contexts,
        "current_context": result.current_context,
        "message": None,
        "guidance": [],
    }
