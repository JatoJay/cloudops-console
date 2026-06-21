from app.kubernetes.deployment_inspector import DeploymentInspector
from app.kubernetes.events_analyzer import EventsAnalyzer
from tests.fakes import FakeExecutor


def test_events_analyzer_summarizes_relevant_reasons() -> None:
    events = {
        "items": [
            {
                "metadata": {"namespace": "default"},
                "reason": "FailedScheduling",
                "message": "0/3 nodes are available",
                "count": 4,
                "involvedObject": {"kind": "Pod", "name": "api"},
            },
            {"reason": "Pulled", "message": "Image pulled"},
        ]
    }
    executor = FakeExecutor({("get", "events", "-A", "-o", "json"): events})

    result = EventsAnalyzer(executor).analyze()

    assert result["healthy"] is False
    assert result["findings"][0]["reason"] == "FailedScheduling"
    assert result["findings"][0]["resource"] == "Pod/api"


def test_events_analyzer_recognizes_image_pull_failure_messages() -> None:
    events = {
        "items": [
            {
                "metadata": {"namespace": "default"},
                "reason": "Failed",
                "message": 'Failed to pull image "api:bad-tag": manifest unknown',
                "involvedObject": {"kind": "Pod", "name": "api"},
            }
        ]
    }
    result = EventsAnalyzer(
        FakeExecutor({("get", "events", "-A", "-o", "json"): events})
    ).analyze()

    assert result["findings"][0]["reason"] == "FailedPull"


def test_deployment_inspector_detects_rollout_failure() -> None:
    deployments = {
        "items": [
            {
                "metadata": {"name": "api", "namespace": "default"},
                "spec": {"replicas": 3},
                "status": {
                    "availableReplicas": 1,
                    "unavailableReplicas": 2,
                    "conditions": [
                        {
                            "type": "Progressing",
                            "status": "False",
                            "reason": "ProgressDeadlineExceeded",
                            "message": "ReplicaSet timed out",
                        }
                    ],
                },
            }
        ]
    }
    executor = FakeExecutor({("get", "deployments", "-A", "-o", "json"): deployments})

    result = DeploymentInspector(executor).inspect()

    deployment = result["unhealthy_deployments"][0]
    assert deployment["available_replicas"] == 1
    assert deployment["unavailable_replicas"] == 2
    assert deployment["conditions"][0]["reason"] == "ProgressDeadlineExceeded"
