from app.kubernetes.network_inspector import NetworkInspector
from tests.fakes import FakeExecutor


def test_network_inspector_detects_selector_and_endpoint_problems() -> None:
    responses = {
        ("get", "services", "-A", "-o", "json"): {
            "items": [
                {
                    "metadata": {"name": "missing-pods", "namespace": "default"},
                    "spec": {"selector": {"app": "missing"}},
                },
                {
                    "metadata": {"name": "api", "namespace": "default"},
                    "spec": {"selector": {"app": "api"}},
                },
            ]
        },
        ("get", "endpoints", "-A", "-o", "json"): {
            "items": [
                {"metadata": {"name": "api", "namespace": "default"}, "subsets": []},
            ]
        },
        ("get", "pods", "-A", "-o", "json"): {
            "items": [
                {
                    "metadata": {
                        "name": "api-123",
                        "namespace": "default",
                        "labels": {"app": "api"},
                    }
                }
            ]
        },
        ("get", "pods", "-n", "kube-system", "-l", "k8s-app=kube-dns", "-o", "json"): {
            "items": [
                {
                    "status": {
                        "phase": "Running",
                        "containerStatuses": [{"ready": True}],
                    }
                }
            ]
        },
    }

    result = NetworkInspector(FakeExecutor(responses)).inspect()

    assert result["healthy"] is False
    assert {issue["type"] for issue in result["issues"]} == {
        "SelectorMismatch",
        "MissingEndpoints",
    }
    assert result["dns"]["healthy"] is True
