from datetime import UTC, datetime, timedelta

from app.kubernetes.pod_inspector import PodInspector
from tests.fakes import FakeExecutor


def _pod(name: str, phase: str, state: dict, *, last_state: dict | None = None) -> dict:
    return {
        "metadata": {
            "name": name,
            "namespace": "default",
            "creationTimestamp": (datetime.now(UTC) - timedelta(minutes=10)).isoformat(),
        },
        "status": {
            "phase": phase,
            "containerStatuses": [
                {
                    "restartCount": 3,
                    "state": state,
                    "lastState": last_state or {},
                }
            ],
        },
    }


def test_pod_inspector_detects_requested_problem_states() -> None:
    pods = [
        _pod("payments", "Running", {"waiting": {"reason": "CrashLoopBackOff"}}),
        _pod("worker", "Pending", {"waiting": {"reason": "ContainerCreating"}}),
        _pod(
            "memory-hog",
            "Running",
            {"running": {}},
            last_state={"terminated": {"reason": "OOMKilled"}},
        ),
        _pod("healthy", "Running", {"running": {}}),
    ]
    executor = FakeExecutor({("get", "pods", "-A", "-o", "json"): {"items": pods}})

    result = PodInspector(executor).inspect()

    assert result["healthy"] is False
    assert result["total_pods"] == 4
    assert {pod["status"] for pod in result["problematic_pods"]} == {
        "CrashLoopBackOff",
        "ContainerCreating",
        "OOMKilled",
    }


def test_pod_inspector_prioritizes_oom_over_generic_restart_backoff() -> None:
    pod = _pod(
        "memory-hog",
        "Running",
        {"waiting": {"reason": "CrashLoopBackOff"}},
        last_state={"terminated": {"reason": "OOMKilled"}},
    )
    result = PodInspector(
        FakeExecutor({("get", "pods", "-A", "-o", "json"): {"items": [pod]}})
    ).inspect()

    assert result["problematic_pods"][0]["status"] == "OOMKilled"
