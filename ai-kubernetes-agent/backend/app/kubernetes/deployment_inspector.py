from typing import Any

from app.kubernetes.executor import KubectlExecutor
from app.kubernetes.parsing import error_payload, parse_json_output


class DeploymentInspector:
    def __init__(self, executor: KubectlExecutor) -> None:
        self.executor = executor

    def inspect(self) -> dict[str, Any]:
        result = self.executor.execute(["get", "deployments", "-A", "-o", "json"])
        payload, error = parse_json_output(result)
        if error:
            return {**error_payload(error), "total_deployments": 0, "unhealthy_deployments": []}

        items = payload.get("items", []) if payload else []
        unhealthy: list[dict[str, Any]] = []

        for deployment in items:
            spec = deployment.get("spec", {})
            status = deployment.get("status", {})
            desired = spec.get("replicas", 1)
            available = status.get("availableReplicas", 0)
            unavailable = status.get("unavailableReplicas", max(desired - available, 0))
            failing_conditions = self._failing_conditions(status.get("conditions", []))

            if available < desired or unavailable > 0 or failing_conditions:
                metadata = deployment.get("metadata", {})
                unhealthy.append(
                    {
                        "name": metadata.get("name", "unknown"),
                        "namespace": metadata.get("namespace", "default"),
                        "desired_replicas": desired,
                        "available_replicas": available,
                        "unavailable_replicas": unavailable,
                        "conditions": failing_conditions,
                    }
                )

        return {
            "healthy": not unhealthy,
            "total_deployments": len(items),
            "unhealthy_deployments": unhealthy,
        }

    @staticmethod
    def _failing_conditions(conditions: list[dict[str, Any]]) -> list[dict[str, str]]:
        failures = []
        for condition in conditions:
            condition_type = condition.get("type")
            condition_status = condition.get("status")
            failed = (
                condition_type in {"Available", "Progressing"} and condition_status == "False"
            ) or (condition_type == "ReplicaFailure" and condition_status == "True")
            if failed:
                failures.append(
                    {
                        "type": condition_type,
                        "reason": condition.get("reason", "Unknown"),
                        "message": condition.get("message", ""),
                    }
                )
        return failures
