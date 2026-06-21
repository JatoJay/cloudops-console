import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from app.ai_analyzer import AIAnalyzer
from app.api.routes.analysis import get_ai_analyzer, get_cloud_scanner
from app.cloud_scanner import CloudScanner, CloudScannerError
from app.main import app
from app.models.auth import AuthContext
from app.models.cost_analysis import CostAnalysis
from app.services.analyses import get_analysis_store
from app.services.insforge import require_auth_context, require_websocket_auth
from app.services.cluster_agents import get_cluster_agent_store


ANALYSIS = {
    "summary": "One unattached disk can be removed after review.",
    "issues": [
        {
            "resource_id": "/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Compute/disks/old",
            "resource_name": "old",
            "category": "unused_or_idle",
            "severity": "medium",
            "finding": "The inventory marks this disk as unattached.",
            "rationale": "Unattached managed disks continue to incur storage charges.",
            "estimated_savings": {"monthly": 5, "annual": 60, "currency": "USD"},
            "fix_commands": ["az disk delete --ids '/subscriptions/sub/resourceGroups/rg/providers/Microsoft.Compute/disks/old'"],
        }
    ],
    "estimated_savings": {"monthly": 5, "annual": 60, "currency": "USD"},
    "assumptions": ["Actual billing and utilization metrics were not supplied."],
}


class RecordingClient:
    def __init__(self) -> None:
        self.messages: list[dict[str, str]] = []
        self.schema: dict[str, Any] = {}

    async def complete(
        self, messages: list[dict[str, str]], response_schema: dict[str, Any]
    ) -> dict[str, Any]:
        self.messages = messages
        self.schema = response_schema
        return ANALYSIS


@pytest.mark.anyio
async def test_analyzer_builds_inventory_prompt_and_validates_response() -> None:
    client = RecordingClient()
    analyzer = AIAnalyzer(client)  # type: ignore[arg-type]

    result = await analyzer.analyze(
        [
            {
                "provider": "gcp",
                "id": "//compute.googleapis.com/projects/test/zones/us-central1-a/instances/vm-1",
                "name": "vm-1",
            }
        ]
    )

    assert isinstance(result, CostAnalysis)
    assert result.issues[0].severity == "medium"
    assert "vm-1" in client.messages[1]["content"]
    assert "untrusted data" in client.messages[0]["content"]
    assert client.schema["properties"]["issues"]


def test_cloud_scanner_normalizes_cli_inventory(monkeypatch: pytest.MonkeyPatch) -> None:
    class Result:
        returncode = 0
        stderr = ""
        stdout = json.dumps(
            [
                {
                    "name": "//compute.googleapis.com/projects/test-project/zones/us-central1-a/instances/vm-1",
                    "displayName": "vm-1",
                    "assetType": "compute.googleapis.com/Instance",
                    "project": "projects/123456789",
                    "location": "us-central1-a",
                    "labels": None,
                }
            ]
        )

    commands: list[list[str]] = []

    def run(command: list[str], **_: Any) -> Result:
        commands.append(command)
        return Result()

    monkeypatch.setattr("app.cloud_scanner.subprocess.run", run)

    resources = CloudScanner(project_id="test-project").scan()

    assert resources[0]["provider"] == "gcp"
    assert resources[0]["project_id"] == "projects/123456789"
    assert resources[0]["labels"] == {}
    assert commands[0][1:3] == ["asset", "search-all-resources"]
    assert "--scope=projects/test-project" in commands[0]


def test_cloud_scanner_surfaces_cli_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    class Result:
        returncode = 1
        stderr = "Please run gcloud auth login"
        stdout = ""

    monkeypatch.setattr("app.cloud_scanner.subprocess.run", lambda *args, **kwargs: Result())

    with pytest.raises(CloudScannerError, match="gcloud auth login"):
        CloudScanner(project_id="test-project").scan()


def test_analyze_endpoint_scans_before_analyzing() -> None:
    calls: list[str] = []
    analysis_id = uuid4()
    user_id = uuid4()

    class Scanner:
        def resource_groups(self) -> list[str]:
            calls.append("groups")
            return ["test-project"]

        def scan(self, resource_group: str) -> list[dict[str, Any]]:
            calls.append("scan")
            assert resource_group == "test-project"
            return [{"provider": "gcp", "name": "vm-1"}]

    class Analyzer:
        async def analyze(self, resources: list[dict[str, Any]]) -> CostAnalysis:
            calls.append("analyze")
            assert resources[0]["name"] == "vm-1"
            return CostAnalysis.model_validate(ANALYSIS)

    class Store:
        def create_completed(
            self,
            stored_id: UUID,
            stored_user_id: UUID,
            resource_group: str,
            resources_scanned: int,
            analysis: CostAnalysis,
        ) -> None:
            calls.append("store")
            assert stored_id == analysis_id
            assert stored_user_id == user_id
            assert resource_group == "test-project"
            assert resources_scanned == 1
            assert analysis.summary == ANALYSIS["summary"]

    app.dependency_overrides[get_cloud_scanner] = Scanner
    app.dependency_overrides[get_ai_analyzer] = Analyzer
    app.dependency_overrides[require_auth_context] = lambda: AuthContext(
        user_id=user_id, access_token="token"
    )
    app.dependency_overrides[get_analysis_store] = Store
    try:
        with TestClient(app) as client:
            response = client.post("/api/analyze", json={"analysis_id": str(analysis_id)})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert calls == ["groups", "scan", "analyze", "store"]
    assert response.json()["analysis_id"] == str(analysis_id)
    assert response.json()["estimated_savings"]["annual"] == 60


def test_history_returns_authenticated_users_analyses() -> None:
    analysis_id = uuid4()

    class Store:
        def list_for_user(self) -> list[dict[str, Any]]:
            return [
                {
                    "id": analysis_id,
                    "resource_group": "test-project",
                    "resources_scanned": 3,
                    "issues_found": 1,
                    "estimated_savings": '{"monthly":5,"annual":60,"currency":"USD"}',
                    "analysis_result": ANALYSIS,
                    "status": "completed",
                    "created_at": datetime.now(UTC),
                }
            ]

    app.dependency_overrides[get_analysis_store] = Store
    try:
        with TestClient(app) as client:
            response = client.get("/api/history")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()[0]["id"] == str(analysis_id)
    assert response.json()[0]["analysis_result"]["issues"][0]["severity"] == "medium"


def test_resource_groups_returns_provider_scan_boundaries() -> None:
    class AgentStore:
        async def list_clusters(self, provider: str) -> list[dict[str, Any]]:
            assert provider == "gcp"
            return [{
                "id": str(uuid4()),
                "status": "online",
                "metadata": {"projects": [
                    {"project_id": "finops-production", "display_name": "Production"},
                    {"project_id": "finops-staging", "display_name": "Staging"},
                ]},
            }]

    app.dependency_overrides[get_cluster_agent_store] = AgentStore
    app.dependency_overrides[require_auth_context] = lambda: AuthContext(
        user_id=uuid4(), access_token="token"
    )
    try:
        with TestClient(app) as client:
            response = client.get("/api/resource-groups")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["resource_groups"] == ["finops-production", "finops-staging"]
    assert response.json()["projects"][0]["display_name"] == "Production"


def test_progress_websocket_replays_messages_in_order() -> None:
    from app.services.progress import progress_broker

    analysis_id = uuid4()
    messages = [
        "Fetching cloud projects...",
        "Scanning resources in test-project...",
        "Analyzing costs with AI...",
        "Storing results...",
        "Analysis complete",
    ]

    async def seed() -> None:
        for message in messages:
            await progress_broker.publish(analysis_id, message)

    import asyncio

    asyncio.run(seed())
    app.dependency_overrides[require_websocket_auth] = lambda: AuthContext(
        user_id=uuid4(), access_token="token"
    )
    with TestClient(app) as client:
        try:
            with client.websocket_connect(
                f"/ws/progress/{analysis_id}", subprotocols=["bearer", "token"]
            ) as websocket:
                received = [websocket.receive_text() for _ in messages]
        finally:
            app.dependency_overrides.clear()

    assert received == messages


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/api/analyze"),
        ("get", "/api/history"),
        ("get", "/api/resource-groups"),
    ],
)
def test_cost_analysis_endpoints_require_jwt(method: str, path: str) -> None:
    with TestClient(app) as client:
        response = getattr(client, method)(path)

    assert response.status_code == 401
    assert response.json()["detail"] == "A valid InsForge session is required"
