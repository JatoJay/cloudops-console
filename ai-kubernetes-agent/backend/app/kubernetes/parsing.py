import json
from typing import Any

from app.kubernetes.executor import CommandResult


def parse_json_output(result: CommandResult) -> tuple[dict[str, Any] | None, str | None]:
    if not result.success:
        detail = concise_error(result.stderr or result.error or "kubectl command failed")
        return None, detail

    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        return None, f"kubectl returned invalid JSON: {exc.msg}"

    if not isinstance(payload, dict):
        return None, "kubectl returned an unexpected JSON value"
    return payload, None


def error_payload(error: str) -> dict[str, object]:
    return {"healthy": False, "error": error}


def concise_error(message: str, max_characters: int = 500) -> str:
    lines = [line.strip() for line in message.splitlines() if line.strip()]
    useful_lines = [line for line in lines if "memcache.go" not in line]
    summary = (useful_lines or lines or ["kubectl command failed"])[-1]
    if len(summary) <= max_characters:
        return summary
    return f"{summary[: max_characters - 3]}..."
