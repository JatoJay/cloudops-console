import argparse
import asyncio
import json
import os
import subprocess
from typing import Any

import httpx
import websockets

from app.cloud_scanner import CloudScanner
from app.core.config import get_settings


class GCPConnector:
    """Runs beside the user's gcloud session and sends inventory, never credentials."""

    def __init__(self, control_plane: str, token: str, connection_name: str) -> None:
        self.control_plane = control_plane.rstrip("/")
        self.token = token
        self.connection_name = connection_name

    async def pair(self) -> str:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{self.control_plane}/api/agents/pair",
                json={
                    "token": self.token,
                    "cluster_name": self.connection_name,
                    "provider": "gcp",
                },
            )
            response.raise_for_status()
            return response.json()["cluster_id"]

    def projects(self) -> list[dict[str, str]]:
        result = subprocess.run(
            ["gcloud", "projects", "list", "--filter=lifecycleState:ACTIVE", "--format=json"],
            capture_output=True,
            check=False,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            detail = result.stderr.strip().splitlines()
            raise RuntimeError(detail[-1] if detail else "Unable to list Google Cloud projects")
        payload = json.loads(result.stdout)
        return [
            {
                "project_id": str(item.get("projectId", "")),
                "display_name": str(item.get("name") or item.get("projectId", "")),
                "lifecycle_state": str(item.get("lifecycleState", "ACTIVE")),
            }
            for item in payload
            if isinstance(item, dict) and item.get("projectId")
        ]

    async def run(self) -> None:
        connection_id = await self.pair()
        scheme = "wss" if self.control_plane.startswith("https://") else "ws"
        host = self.control_plane.split("://", 1)[-1]
        uri = f"{scheme}://{host}/api/ws/agent/{connection_id}"
        while True:
            try:
                async with websockets.connect(
                    uri, subprotocols=["agent", self.token], ping_interval=20, max_size=16 * 1024 * 1024
                ) as socket:
                    await socket.send(json.dumps({"type": "projects", "projects": await asyncio.to_thread(self.projects)}))
                    heartbeat = asyncio.create_task(self.send_heartbeats(socket))
                    try:
                        async for raw in socket:
                            message = json.loads(raw)
                            if message.get("type") == "job":
                                asyncio.create_task(self.execute_job(socket, message))
                    finally:
                        heartbeat.cancel()
            except Exception as exc:
                print(f"Cloud connector disconnected: {type(exc).__name__}; retrying in 5s", flush=True)
                await asyncio.sleep(5)

    async def send_heartbeats(self, socket: Any) -> None:
        while True:
            await socket.send(json.dumps({"type": "heartbeat"}))
            await asyncio.sleep(25)

    async def execute_job(self, socket: Any, job: dict[str, Any]) -> None:
        job_id = job["job_id"]
        try:
            if job.get("job_type") != "cloud_cost_analysis":
                raise RuntimeError("Unsupported cloud connector job")
            project_id = str(job.get("payload", {}).get("project_id", "")).strip()
            if not project_id:
                raise RuntimeError("A Google Cloud project is required")
            await socket.send(json.dumps({
                "type": "progress", "job_id": job_id,
                "message": f"Scanning read-only inventory in {project_id}",
            }))
            settings = get_settings()
            resources = await asyncio.to_thread(
                CloudScanner(project_id=project_id, timeout_seconds=settings.cloud_scan_timeout_seconds).scan
            )
            await socket.send(json.dumps({
                "type": "result", "job_id": job_id,
                "result": {"project_id": project_id, "resources": resources},
            }))
        except Exception as exc:
            await socket.send(json.dumps({
                "type": "failed", "job_id": job_id, "error": str(exc)[:2000],
            }))


def main() -> None:
    parser = argparse.ArgumentParser(description="CloudOps Console read-only GCP connector")
    parser.add_argument("--control-plane", default=os.getenv("CONTROL_PLANE_URL", "http://localhost:8000"))
    parser.add_argument("--token", default=os.getenv("PAIRING_TOKEN"), required=not os.getenv("PAIRING_TOKEN"))
    parser.add_argument("--connection-name", default=os.getenv("CONNECTION_NAME", "Google Cloud"))
    args = parser.parse_args()
    asyncio.run(GCPConnector(args.control_plane, args.token, args.connection_name).run())


if __name__ == "__main__":
    main()
