import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import httpx
from fastapi import HTTPException, WebSocket
from loguru import logger


def hash_agent_secret(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class ClusterAgentStore:
    def __init__(self, base_url: str, bearer: str, timeout: float = 15.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.bearer = bearer
        self.timeout = timeout

    async def request(self, table: str, method: str = "GET", *, params=None, json=None) -> Any:
        if not self.base_url or not self.bearer:
            raise HTTPException(503, "Cluster agent storage is not configured")
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method,
                    f"{self.base_url}/api/database/records/{table}",
                    params=params,
                    json=json,
                    headers={
                        "Authorization": f"Bearer {self.bearer}",
                        "Content-Type": "application/json",
                        "Prefer": "return=representation",
                    },
                )
        except httpx.RequestError as exc:
            raise HTTPException(503, "Cluster agent storage is temporarily unavailable") from exc
        if response.status_code in {401, 403}:
            raise HTTPException(403, "Cluster agent access denied")
        if response.is_error:
            logger.error("Cluster agent storage returned HTTP {}", response.status_code)
            raise HTTPException(503, "Cluster agent storage is temporarily unavailable")
        return response.json() if response.content else None

    async def create_pairing_token(self, user_id: UUID, cluster_name: str) -> tuple[str, datetime]:
        token = f"coa_{secrets.token_urlsafe(32)}"
        expires_at = datetime.now(UTC) + timedelta(minutes=15)
        await self.request("cluster_pairing_tokens", "POST", json={
            "user_id": str(user_id), "cluster_name": cluster_name,
            "token_hash": hash_agent_secret(token), "expires_at": expires_at.isoformat(),
        })
        return token, expires_at

    async def list_clusters(self) -> list[dict[str, Any]]:
        return await self.request("connected_clusters", params={
            "select": "id,name,provider,status,last_seen,created_at", "order": "created_at.desc"
        }) or []

    async def delete_cluster(self, cluster_id: UUID) -> None:
        rows = await self.request("connected_clusters", "DELETE", params={"id": f"eq.{cluster_id}"})
        if not rows:
            raise HTTPException(404, "Cluster connection not found")

    async def create_job(self, user_id: UUID, cluster_id: UUID, job_type: str, payload: dict) -> dict:
        rows = await self.request("cluster_jobs", "POST", json={
            "user_id": str(user_id), "cluster_id": str(cluster_id),
            "job_type": job_type, "payload": payload,
        })
        if not rows:
            raise HTTPException(404, "Cluster connection not found")
        return rows[0]

    async def list_jobs(self, cluster_id: UUID) -> list[dict[str, Any]]:
        return await self.request("cluster_jobs", params={
            "cluster_id": f"eq.{cluster_id}", "order": "created_at.desc", "limit": "50"
        }) or []


class AgentAdminStore(ClusterAgentStore):
    async def pair(self, token: str, cluster_name: str) -> UUID:
        token_hash = hash_agent_secret(token)
        existing = await self.request("connected_clusters", params={
            "agent_secret_hash": f"eq.{token_hash}", "select": "id,status", "limit": "1"
        })
        if existing and existing[0]["status"] != "revoked":
            return UUID(existing[0]["id"])
        rows = await self.request("cluster_pairing_tokens", params={
            "token_hash": f"eq.{token_hash}", "used_at": "is.null",
            "expires_at": f"gt.{datetime.now(UTC).isoformat()}", "select": "id,user_id,cluster_name", "limit": "1",
        })
        if not rows:
            raise HTTPException(401, "Pairing token is invalid or expired")
        pairing = rows[0]
        clusters = await self.request("connected_clusters", "POST", json={
            "user_id": pairing["user_id"], "name": cluster_name or pairing["cluster_name"],
            "agent_secret_hash": token_hash, "status": "offline",
        })
        await self.request("cluster_pairing_tokens", "PATCH", params={"id": f"eq.{pairing['id']}"}, json={"used_at": datetime.now(UTC).isoformat()})
        return UUID(clusters[0]["id"])

    async def authenticate_agent(self, cluster_id: UUID, token: str) -> bool:
        rows = await self.request("connected_clusters", params={
            "id": f"eq.{cluster_id}", "agent_secret_hash": f"eq.{hash_agent_secret(token)}",
            "status": "neq.revoked", "select": "id", "limit": "1",
        })
        return bool(rows)

    async def mark_cluster(self, cluster_id: UUID, status: str) -> None:
        now = datetime.now(UTC).isoformat()
        await self.request("connected_clusters", "PATCH", params={"id": f"eq.{cluster_id}"}, json={"status": status, "last_seen": now, "updated_at": now})

    async def queued_jobs(self, cluster_id: UUID) -> list[dict]:
        return await self.request("cluster_jobs", params={"cluster_id": f"eq.{cluster_id}", "status": "eq.queued", "order": "created_at.asc"}) or []

    async def update_job(self, job_id: UUID, **values: Any) -> None:
        values["updated_at"] = datetime.now(UTC).isoformat()
        await self.request("cluster_jobs", "PATCH", params={"id": f"eq.{job_id}"}, json=values)

    async def append_progress(self, job_id: UUID, message: str) -> None:
        rows = await self.request("cluster_jobs", params={"id": f"eq.{job_id}", "select": "progress", "limit": "1"})
        progress = (rows[0].get("progress") or []) if rows else []
        progress.append({"message": message, "at": datetime.now(UTC).isoformat()})
        await self.update_job(job_id, status="running", progress=progress, started_at=datetime.now(UTC).isoformat())


class AgentConnectionManager:
    def __init__(self) -> None:
        self.connections: dict[UUID, WebSocket] = {}

    async def connect(self, cluster_id: UUID, websocket: WebSocket) -> None:
        await websocket.accept(subprotocol="agent")
        self.connections[cluster_id] = websocket

    def disconnect(self, cluster_id: UUID) -> None:
        self.connections.pop(cluster_id, None)

    async def dispatch(self, job: dict) -> bool:
        websocket = self.connections.get(UUID(job["cluster_id"]))
        if not websocket:
            return False
        await websocket.send_json({"type": "job", "job_id": job["id"], "job_type": job["job_type"], "payload": job.get("payload") or {}})
        return True


agent_connections = AgentConnectionManager()
