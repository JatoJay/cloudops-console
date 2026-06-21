from typing import Any
from uuid import UUID

import httpx
from fastapi import Depends, Header, HTTPException, WebSocket, WebSocketException, status
from loguru import logger

from app.core.config import Settings, get_settings
from app.models.auth import AuthContext


class InsForgeAuthService:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float = 15.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    async def authenticate(self, access_token: str) -> AuthContext:
        if not self.base_url:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="InsForge authentication is not configured",
            )

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.get(
                    f"{self.base_url}/api/auth/sessions/current",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
        except httpx.RequestError as exc:
            logger.error("InsForge authentication request failed: {}", type(exc).__name__)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service is temporarily unavailable",
            ) from exc

        if response.status_code in {401, 403}:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="A valid InsForge session is required",
            )
        if response.is_error:
            logger.error("InsForge authentication returned HTTP {}", response.status_code)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service is temporarily unavailable",
            )

        try:
            user = response.json()["user"]
            return AuthContext(
                user_id=UUID(user["id"]),
                email=user.get("email"),
                access_token=access_token,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="A valid InsForge session is required",
            ) from exc


class InvestigationRunStore:
    """Persist user-owned investigation progress through InsForge RLS."""

    def __init__(
        self,
        base_url: str,
        access_token: str,
        timeout_seconds: float = 15.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.access_token = access_token
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    def create(self, run_id: UUID, user_id: UUID, namespace: str) -> None:
        self._request(
            "POST",
            json={
                "id": str(run_id),
                "user_id": str(user_id),
                "namespace": namespace,
                "status": "queued",
                "current_step": "queued",
            },
        )

    def ensure_owned(self, run_id: UUID) -> None:
        rows = self._request(
            "GET",
            params={"id": f"eq.{run_id}", "select": "id", "limit": "1"},
        )
        if not isinstance(rows, list) or not rows:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation not found")

    def update(self, run_id: UUID, **values: object) -> None:
        rows = self._request(
            "PATCH",
            params={"id": f"eq.{run_id}"},
            json=values,
        )
        if not isinstance(rows, list) or not rows:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation not found")

    def _request(
        self,
        method: str,
        *,
        params: dict[str, str] | None = None,
        json: dict[str, object] | None = None,
    ) -> Any:
        try:
            with httpx.Client(timeout=self.timeout_seconds, transport=self.transport) as client:
                response = client.request(
                    method,
                    f"{self.base_url}/api/database/records/investigation_runs",
                    params=params,
                    json=json,
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "Content-Type": "application/json",
                        "Prefer": "return=representation",
                    },
                )
        except httpx.RequestError as exc:
            logger.error("InsForge history request failed: {}", type(exc).__name__)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Investigation history is temporarily unavailable",
            ) from exc

        if response.status_code in {401, 403}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Investigation access denied")
        if response.is_error:
            logger.error("InsForge history request returned HTTP {}", response.status_code)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Investigation history is temporarily unavailable",
            )
        return response.json() if response.content else None


def get_auth_service(settings: Settings = Depends(get_settings)) -> InsForgeAuthService:
    return InsForgeAuthService(settings.insforge_url, settings.insforge_timeout_seconds)


async def require_auth_context(
    authorization: str | None = Header(default=None),
    auth_service: InsForgeAuthService = Depends(get_auth_service),
) -> AuthContext:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid InsForge session is required",
        )
    return await auth_service.authenticate(authorization.removeprefix("Bearer ").strip())


async def require_websocket_auth(
    websocket: WebSocket,
    auth_service: InsForgeAuthService = Depends(get_auth_service),
) -> AuthContext:
    """Authenticate browser WebSockets without putting JWTs in logged URLs."""
    protocols = [value.strip() for value in websocket.headers.get("sec-websocket-protocol", "").split(",")]
    access_token = protocols[1] if len(protocols) == 2 and protocols[0] == "bearer" else None
    if not access_token:
        raise WebSocketException(code=1008, reason="A valid InsForge session is required")
    try:
        return await auth_service.authenticate(access_token)
    except HTTPException as exc:
        raise WebSocketException(code=1008, reason="A valid InsForge session is required") from exc


def get_run_store(
    auth: AuthContext = Depends(require_auth_context),
    settings: Settings = Depends(get_settings),
) -> InvestigationRunStore:
    return InvestigationRunStore(
        settings.insforge_url,
        auth.access_token,
        settings.insforge_timeout_seconds,
    )
