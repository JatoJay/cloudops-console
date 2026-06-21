import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

import httpx
import websockets

from app.core.config import get_settings
from app.kubernetes.vulnerability_scanner import VulnerabilityScanner
from app.services.investigation import InvestigationService


def write_in_cluster_kubeconfig(path: str) -> str:
    host = os.getenv("KUBERNETES_SERVICE_HOST")
    port = os.getenv("KUBERNETES_SERVICE_PORT_HTTPS", "443")
    if not host:
        return os.getenv("KUBECONFIG", path)
    payload = {
        "apiVersion": "v1", "kind": "Config", "current-context": "in-cluster",
        "clusters": [{"name": "in-cluster", "cluster": {
            "server": f"https://{host}:{port}",
            "certificate-authority": "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"}}],
        "users": [{"name": "agent", "user": {"tokenFile": "/var/run/secrets/kubernetes.io/serviceaccount/token"}}],
        "contexts": [{"name": "in-cluster", "context": {"cluster": "in-cluster", "user": "agent"}}],
    }
    Path(path).write_text(json.dumps(payload), encoding="utf-8")
    return path


class ClusterAgent:
    def __init__(self, control_plane: str, token: str, cluster_name: str, kubeconfig: str) -> None:
        self.control_plane = control_plane.rstrip("/")
        self.token = token
        self.cluster_name = cluster_name
        self.kubeconfig = kubeconfig

    async def pair(self) -> str:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(f"{self.control_plane}/api/agents/pair", json={"token": self.token, "cluster_name": self.cluster_name})
            response.raise_for_status()
            return response.json()["cluster_id"]

    async def run(self) -> None:
        cluster_id = await self.pair()
        scheme = "wss" if self.control_plane.startswith("https://") else "ws"
        host = self.control_plane.split("://", 1)[-1]
        uri = f"{scheme}://{host}/api/ws/agent/{cluster_id}"
        while True:
            try:
                async with websockets.connect(uri, subprotocols=["agent", self.token], ping_interval=20) as socket:
                    heartbeat = asyncio.create_task(self.send_heartbeats(socket))
                    try:
                        async for raw in socket:
                            message = json.loads(raw)
                            if message.get("type") == "job":
                                asyncio.create_task(self.execute_job(socket, message))
                    finally:
                        heartbeat.cancel()
            except Exception as exc:
                print(f"Agent disconnected: {type(exc).__name__}; retrying in 5s", flush=True)
                await asyncio.sleep(5)

    async def send_heartbeats(self, socket: Any) -> None:
        while True:
            await socket.send(json.dumps({"type": "heartbeat"}))
            await asyncio.sleep(25)

    async def execute_job(self, socket: Any, job: dict[str, Any]) -> None:
        job_id = job["job_id"]
        try:
            await socket.send(json.dumps({"type": "progress", "job_id": job_id, "message": "Collecting read-only cluster evidence"}))
            settings = get_settings().model_copy(update={"kubeconfig_path": self.kubeconfig})
            if job["job_type"] == "investigate":
                result = await asyncio.to_thread(InvestigationService.from_settings(settings, "in-cluster").investigate)
            else:
                result = (await asyncio.to_thread(VulnerabilityScanner(self.kubeconfig, settings.vulnerability_scan_timeout_seconds).scan, "in-cluster")).model_dump(mode="json")
            await socket.send(json.dumps({"type": "result", "job_id": job_id, "result": result}))
        except Exception as exc:
            await socket.send(json.dumps({"type": "failed", "job_id": job_id, "error": str(exc)}))


def main() -> None:
    parser = argparse.ArgumentParser(description="CloudOps Console read-only Kubernetes agent")
    parser.add_argument("--control-plane", default=os.getenv("CONTROL_PLANE_URL", "http://localhost:8000"))
    parser.add_argument("--token", default=os.getenv("PAIRING_TOKEN"), required=not os.getenv("PAIRING_TOKEN"))
    parser.add_argument("--cluster-name", default=os.getenv("CLUSTER_NAME", "kubernetes-cluster"))
    default_kubeconfig = os.getenv("KUBECONFIG_PATH") or os.getenv("KUBECONFIG") or str(Path.home() / ".kube" / "config")
    parser.add_argument("--kubeconfig", default=default_kubeconfig)
    args = parser.parse_args()
    kubeconfig = write_in_cluster_kubeconfig(args.kubeconfig)
    asyncio.run(ClusterAgent(args.control_plane, args.token, args.cluster_name, kubeconfig).run())


if __name__ == "__main__":
    main()
