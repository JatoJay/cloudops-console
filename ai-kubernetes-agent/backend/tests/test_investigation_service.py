from typing import Any

from app.services.investigation import InvestigationService


class Recorder:
    def __init__(self, name: str, calls: list[str], result: dict[str, Any]) -> None:
        self.name = name
        self.calls = calls
        self.result = result

    def inspect(self) -> dict[str, Any]:
        self.calls.append(self.name)
        return self.result

    def analyze(self) -> dict[str, Any]:
        self.calls.append(self.name)
        return self.result


class LogsRecorder(Recorder):
    def collect(self, problematic_pods: list[dict[str, Any]]) -> dict[str, Any]:
        self.calls.append(self.name)
        assert problematic_pods == [{"name": "api", "namespace": "default"}]
        return self.result


def test_investigation_service_runs_collectors_in_expected_order() -> None:
    calls: list[str] = []
    service = InvestigationService(
        pod_inspector=Recorder(
            "pods",
            calls,
            {"problematic_pods": [{"name": "api", "namespace": "default"}]},
        ),
        logs_collector=LogsRecorder("logs", calls, {}),
        events_analyzer=Recorder("events", calls, {}),
        deployment_inspector=Recorder("deployments", calls, {}),
        network_inspector=Recorder("network", calls, {}),
    )

    result = service.investigate()

    assert calls == ["pods", "logs", "events", "deployments", "network"]
    assert list(result) == ["pods", "logs", "events", "deployments", "network"]
