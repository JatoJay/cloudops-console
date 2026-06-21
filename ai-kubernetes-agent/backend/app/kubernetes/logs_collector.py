import re
from typing import Any

from app.kubernetes.executor import KubectlExecutor
from app.kubernetes.parsing import concise_error


class LogsCollector:
    FAILURE_PATTERN = re.compile(
        r"exception|traceback|error|fatal|panic|connection (?:refused|reset|failed)|"
        r"timed?\s*out|missing|required.+(?:env|environment)|not found|"
        r"failed to (?:start|connect|initialize)|startup|crash",
        re.IGNORECASE,
    )

    def __init__(self, executor: KubectlExecutor, tail_lines: int = 200, max_output_lines: int = 50) -> None:
        self.executor = executor
        self.tail_lines = tail_lines
        self.max_output_lines = max_output_lines

    def collect(self, problematic_pods: list[dict[str, Any]]) -> dict[str, Any]:
        findings: list[dict[str, Any]] = []
        errors: list[str] = []

        for pod in problematic_pods:
            name = str(pod["name"])
            namespace = str(pod["namespace"])
            result = self.executor.execute(
                [
                    "logs",
                    name,
                    "-n",
                    namespace,
                    "--all-containers=true",
                    f"--tail={self.tail_lines}",
                ]
            )

            if not result.success:
                errors.append(
                    f"{namespace}/{name}: {concise_error(result.stderr or result.error or 'logs unavailable')}"
                )
                continue

            all_lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            relevant_lines = [line for line in all_lines if self.FAILURE_PATTERN.search(line)]
            selected_lines = (relevant_lines or all_lines[-20:])[-self.max_output_lines :]

            findings.append(
                {
                    "name": name,
                    "namespace": namespace,
                    "pod_status": pod.get("status", "Unknown"),
                    "relevant_lines": selected_lines,
                    "truncated": len(relevant_lines or all_lines[-20:]) > len(selected_lines),
                }
            )

        return {
            "healthy": not findings and not errors,
            "pods_checked": len(problematic_pods),
            "findings": findings,
            "errors": errors,
        }
