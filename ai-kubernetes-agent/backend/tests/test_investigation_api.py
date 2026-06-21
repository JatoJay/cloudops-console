from typing import Any
from uuid import UUID

from fastapi.testclient import TestClient

from app.ai.agent import get_ai_agent
from app.ai.llm_client import LLMClientError
from app.main import app
from app.models.auth import AuthContext
from app.models.diagnosis import Diagnosis
from app.services.investigation import get_investigation_service
from app.services.insforge import get_run_store, require_auth_context
from app.services.clusters import ClusterContexts, get_cluster_context_service


class FakeInvestigationService:
    def investigate(self, progress=None) -> dict[str, Any]:
        if progress:
            for step in [
                "checking_pods",
                "reading_logs",
                "analyzing_events",
                "inspecting_deployments",
                "checking_networking",
            ]:
                progress(step)
        return {
            "pods": {
                "healthy": False,
                "total_pods": 1,
                "problematic_pods": [
                    {"name": "api", "namespace": "default", "status": "CrashLoopBackOff"}
                ],
            },
            "logs": {"healthy": False, "findings": [{"relevant_lines": ["DATABASE_URL missing"]}], "errors": []},
            "events": {"healthy": True, "findings": []},
            "deployments": {"healthy": True, "unhealthy_deployments": []},
            "network": {"healthy": True, "issues": [], "errors": []},
        }


class FakeAIAgent:
    async def diagnose(self, investigation: dict[str, Any]) -> Diagnosis:
        assert investigation["pods"]["problematic_pods"]
        return Diagnosis(
            root_cause="DATABASE_URL is missing",
            explanation="The application exits during startup.",
            fix="Add DATABASE_URL to the deployment environment.",
            kubectl_commands=["kubectl set env deployment/api DATABASE_URL=<value> -n default"],
            prevention_recommendation="Validate required environment variables in CI.",
            confidence=92,
            confidence_reasoning=["CrashLoopBackOff and logs agree"],
        )


class FailingAIAgent:
    async def diagnose(self, investigation: dict[str, Any]) -> Diagnosis:
        raise LLMClientError("AI reasoning service is temporarily unavailable")


class FakeRunStore:
    def __init__(self) -> None:
        self.updates: list[dict[str, object]] = []

    def create(self, run_id, user_id, namespace) -> None:
        pass

    def ensure_owned(self, run_id) -> None:
        pass

    def update(self, run_id, **values) -> None:
        self.updates.append(values)


class FakeClusterContexts:
    def list_contexts(self) -> ClusterContexts:
        return ClusterContexts(["minikube", "kind-dev"], "minikube")


AUTH = AuthContext(
    user_id=UUID("11111111-1111-4111-8111-111111111111"),
    email="operator@example.com",
    access_token="test-token",
)


def test_investigate_endpoint_returns_combined_evidence() -> None:
    app.dependency_overrides[get_investigation_service] = lambda: FakeInvestigationService()
    app.dependency_overrides[get_ai_agent] = lambda: FakeAIAgent()
    app.dependency_overrides[require_auth_context] = lambda: AUTH
    app.dependency_overrides[get_run_store] = lambda: FakeRunStore()

    try:
        with TestClient(app) as client:
            response = client.post("/investigate")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["investigation_id"]
    assert response.json()["diagnosis"]["confidence"] == 92
    assert response.json()["diagnosis"]["root_cause"] == "DATABASE_URL is missing"
    assert set(response.json()["investigation"]) == {
        "pods",
        "logs",
        "events",
        "deployments",
        "network",
    }


def test_investigate_endpoint_returns_partial_evidence_when_ai_fails() -> None:
    app.dependency_overrides[get_investigation_service] = lambda: FakeInvestigationService()
    app.dependency_overrides[get_ai_agent] = lambda: FailingAIAgent()
    app.dependency_overrides[require_auth_context] = lambda: AUTH
    app.dependency_overrides[get_run_store] = lambda: FakeRunStore()

    try:
        with TestClient(app) as client:
            response = client.post("/investigate")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "partial"
    assert response.json()["diagnosis"] is None
    assert response.json()["errors"] == ["ai: AI reasoning service is temporarily unavailable"]


def test_investigate_endpoint_requires_authentication() -> None:
    with TestClient(app) as client:
        response = client.post("/investigate")

    assert response.status_code == 401


def test_investigate_endpoint_returns_healthy_empty_state_without_ai() -> None:
    class HealthyService:
        def investigate(self, progress=None) -> dict[str, Any]:
            return {
                "pods": {"healthy": True, "total_pods": 2, "problematic_pods": []},
                "logs": {"healthy": True, "findings": [], "errors": []},
                "events": {"healthy": True, "findings": []},
                "deployments": {"healthy": True, "total_deployments": 1, "unhealthy_deployments": []},
                "network": {"healthy": True, "total_services": 1, "issues": [], "errors": []},
            }

    app.dependency_overrides[get_investigation_service] = lambda: HealthyService()
    app.dependency_overrides[get_ai_agent] = lambda: FakeAIAgent()
    app.dependency_overrides[require_auth_context] = lambda: AUTH
    app.dependency_overrides[get_run_store] = lambda: FakeRunStore()
    try:
        with TestClient(app) as client:
            response = client.post("/investigate")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["cluster_healthy"] is True
    assert response.json()["diagnosis"] is None
    assert response.json()["message"] == "No critical Kubernetes issues detected. Cluster appears healthy."


def test_investigate_rejects_context_not_in_kubeconfig() -> None:
    app.dependency_overrides[get_investigation_service] = lambda: FakeInvestigationService()
    app.dependency_overrides[get_ai_agent] = lambda: FakeAIAgent()
    app.dependency_overrides[require_auth_context] = lambda: AUTH
    app.dependency_overrides[get_run_store] = lambda: FakeRunStore()
    app.dependency_overrides[get_cluster_context_service] = lambda: FakeClusterContexts()
    try:
        with TestClient(app) as client:
            response = client.post("/investigate", json={"context": "production"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["detail"]["message"] == "The selected Kubernetes cluster is no longer available."
