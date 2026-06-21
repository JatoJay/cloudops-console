from typing import Any

from app.kubernetes.executor import KubectlExecutor
from app.kubernetes.parsing import error_payload, parse_json_output


class EventsAnalyzer:
    PROBLEM_REASONS = {
        "BackOff",
        "ErrImagePull",
        "FailedMount",
        "FailedPull",
        "FailedScheduling",
        "Unhealthy",
    }

    def __init__(self, executor: KubectlExecutor) -> None:
        self.executor = executor

    def analyze(self) -> dict[str, Any]:
        result = self.executor.execute(["get", "events", "-A", "-o", "json"])
        payload, error = parse_json_output(result)
        if error:
            return {**error_payload(error), "findings": []}

        findings = []
        for event in payload.get("items", []) if payload else []:
            reason = event.get("reason")
            message = event.get("message", "")
            normalized_reason = self._normalized_reason(reason, message)
            if normalized_reason not in self.PROBLEM_REASONS:
                continue
            metadata = event.get("metadata", {})
            involved = event.get("involvedObject", {})
            findings.append(
                {
                    "reason": normalized_reason,
                    "namespace": metadata.get("namespace", involved.get("namespace", "default")),
                    "resource": f"{involved.get('kind', 'Unknown')}/{involved.get('name', 'unknown')}",
                    "message": message,
                    "count": event.get("count", 1),
                    "last_seen": event.get("lastTimestamp") or event.get("eventTime"),
                }
            )

        return {"healthy": not findings, "findings": findings}

    @staticmethod
    def _normalized_reason(reason: str | None, message: str) -> str | None:
        if reason == "Failed" and "pull image" in message.lower():
            return "FailedPull"
        return reason
