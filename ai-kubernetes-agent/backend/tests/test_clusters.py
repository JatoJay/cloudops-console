from fastapi.testclient import TestClient

from app.main import app
from app.models.auth import AuthContext
from app.services.clusters import ClusterContextService, get_cluster_context_service
from app.services.insforge import require_auth_context
from tests.fakes import FakeExecutor


class FakeAuth:
    user_id = "11111111-1111-4111-8111-111111111111"
    email = "operator@example.com"
    access_token = "token"


def test_cluster_service_lists_all_contexts_and_current_context() -> None:
    service = ClusterContextService(
        FakeExecutor(
            {
                ("config", "get-contexts", "-o", "name"): "dev\nstaging\nproduction\n",
                ("config", "current-context"): "staging\n",
            }
        )
    )

    result = service.list_contexts()

    assert result.contexts == ["dev", "staging", "production"]
    assert result.current_context == "staging"
    assert result.error is None


def test_clusters_endpoint_is_protected() -> None:
    with TestClient(app) as client:
        response = client.get("/clusters")
    assert response.status_code == 401


def test_clusters_endpoint_returns_contexts() -> None:
    service = ClusterContextService(
        FakeExecutor(
            {
                ("config", "get-contexts", "-o", "name"): "minikube\nkind-dev",
                ("config", "current-context"): "minikube",
            }
        )
    )
    app.dependency_overrides[require_auth_context] = lambda: FakeAuth()
    app.dependency_overrides[get_cluster_context_service] = lambda: service
    try:
        with TestClient(app) as client:
            response = client.get("/clusters")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["contexts"] == ["minikube", "kind-dev"]
    assert response.json()["current_context"] == "minikube"
