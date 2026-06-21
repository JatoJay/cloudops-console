from datetime import UTC, datetime
from typing import Any

from app.kubernetes.executor import KubectlExecutor
from app.kubernetes.parsing import error_payload, parse_json_output


class PodInspector:
    PROBLEM_STATES = {"CrashLoopBackOff", "ImagePullBackOff", "Error", "OOMKilled"}

    def __init__(self, executor: KubectlExecutor, container_creating_timeout_seconds: int = 300) -> None:
        self.executor = executor
        self.container_creating_timeout_seconds = container_creating_timeout_seconds

    def inspect(self) -> dict[str, Any]:
        result = self.executor.execute(["get", "pods", "-A", "-o", "json"])
        payload, error = parse_json_output(result)
        if error:
            return {**error_payload(error), "total_pods": 0, "problematic_pods": []}

        items = payload.get("items", []) if payload else []
        problematic_pods: list[dict[str, Any]] = []

        for pod in items:
            status = self._problem_status(pod)
            if status:
                metadata = pod.get("metadata", {})
                problematic_pods.append(
                    {
                        "name": metadata.get("name", "unknown"),
                        "namespace": metadata.get("namespace", "default"),
                        "status": status,
                        "restarts": self._restart_count(pod),
                    }
                )

        return {
            "healthy": not problematic_pods,
            "total_pods": len(items),
            "problematic_pods": problematic_pods,
        }

    def _problem_status(self, pod: dict[str, Any]) -> str | None:
        pod_status = pod.get("status", {})
        phase = pod_status.get("phase", "Unknown")

        # Keep the most diagnostic termination reason when Kubernetes has
        # already moved the container into a generic restart backoff state.
        if any(
            container.get("lastState", {}).get("terminated", {}).get("reason") == "OOMKilled"
            for container in self._container_statuses(pod)
        ):
            return "OOMKilled"

        for container in self._container_statuses(pod):
            state = container.get("state", {})
            last_state = container.get("lastState", {})
            waiting_reason = state.get("waiting", {}).get("reason")
            terminated_reason = state.get("terminated", {}).get("reason")
            last_terminated_reason = last_state.get("terminated", {}).get("reason")

            if waiting_reason in self.PROBLEM_STATES:
                return waiting_reason
            if waiting_reason == "ContainerCreating" and self._is_stuck(pod):
                return "ContainerCreating"
            if terminated_reason in self.PROBLEM_STATES:
                return terminated_reason
            if last_terminated_reason in self.PROBLEM_STATES:
                return last_terminated_reason

        if phase == "Pending":
            return "Pending"
        if phase in {"Failed", "Unknown"}:
            return "Error"
        return None

    @staticmethod
    def _container_statuses(pod: dict[str, Any]) -> list[dict[str, Any]]:
        status = pod.get("status", {})
        return [
            *status.get("initContainerStatuses", []),
            *status.get("containerStatuses", []),
        ]

    @classmethod
    def _restart_count(cls, pod: dict[str, Any]) -> int:
        return sum(status.get("restartCount", 0) for status in cls._container_statuses(pod))

    def _is_stuck(self, pod: dict[str, Any]) -> bool:
        created_at = pod.get("metadata", {}).get("creationTimestamp")
        if not created_at:
            return True
        try:
            created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except ValueError:
            return True
        return (datetime.now(UTC) - created).total_seconds() >= self.container_creating_timeout_seconds
