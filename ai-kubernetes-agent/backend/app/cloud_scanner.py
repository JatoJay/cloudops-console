import json
import subprocess
from typing import Any

from fastapi import Depends

from app.core.config import Settings, get_settings


class CloudScannerError(RuntimeError):
    """A safe error raised when cloud inventory cannot be collected."""


class CloudScanner:
    """Collect cloud resources, starting with the active Google Cloud CLI account."""

    def __init__(
        self,
        executable: str = "gcloud",
        project_id: str = "",
        timeout_seconds: int = 60,
    ) -> None:
        self.executable = executable
        self.project_id = project_id
        self.timeout_seconds = timeout_seconds

    def resource_groups(self) -> list[str]:
        """Return scan boundaries; a GCP project is the first provider's boundary."""
        return [self.project_id or self._active_project()]

    def scan(self, resource_group: str | None = None) -> list[dict[str, Any]]:
        project_id = resource_group or self.project_id or self._active_project()
        result = self._run(
            [
                self.executable,
                "asset",
                "search-all-resources",
                f"--scope=projects/{project_id}",
                "--format=json",
            ]
        )

        try:
            resources = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise CloudScannerError("Google Cloud CLI returned invalid resource data") from exc
        if not isinstance(resources, list):
            raise CloudScannerError("Google Cloud CLI returned an invalid resource inventory")

        return [self._normalize(resource, project_id) for resource in resources if isinstance(resource, dict)]

    def _active_project(self) -> str:
        result = self._run(
            [self.executable, "config", "get-value", "project", "--quiet"]
        )
        project_id = result.stdout.strip()
        if not project_id or project_id == "(unset)":
            raise CloudScannerError(
                "No Google Cloud project is configured; set GCP_PROJECT_ID or run "
                "`gcloud config set project PROJECT_ID`"
            )
        return project_id

    def _run(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        try:
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except FileNotFoundError as exc:
            raise CloudScannerError("Google Cloud CLI is not installed") from exc
        except subprocess.TimeoutExpired as exc:
            raise CloudScannerError("Google Cloud resource scan timed out") from exc

        if result.returncode != 0:
            detail = result.stderr.strip().splitlines()
            message = detail[-1] if detail else "Google Cloud CLI resource scan failed"
            raise CloudScannerError(message)
        return result

    @staticmethod
    def _normalize(resource: dict[str, Any], project_id: str) -> dict[str, Any]:
        return {
            "provider": "gcp",
            "id": str(resource.get("name", "")),
            "name": str(resource.get("displayName") or resource.get("name", "")),
            "type": str(resource.get("assetType", "")),
            "project_id": resource.get("project") or project_id,
            "location": resource.get("location"),
            "state": resource.get("state"),
            "labels": resource.get("labels") or {},
            "description": resource.get("description"),
            "additional_attributes": resource.get("additionalAttributes") or {},
        }


def get_cloud_scanner(settings: Settings = Depends(get_settings)) -> CloudScanner:
    return CloudScanner(
        project_id=settings.gcp_project_id,
        timeout_seconds=settings.cloud_scan_timeout_seconds,
    )
