import json
from typing import Any
from uuid import UUID

import httpx
from fastapi import Depends, HTTPException, status
from loguru import logger

from app.core.config import Settings, get_settings
from app.models.auth import AuthContext
from app.models.cost_analysis import AnalysisHistoryItem, CostAnalysis
from app.services.insforge import require_auth_context


class AnalysisStore:
    """Persist and list user-owned cloud cost analyses through InsForge RLS."""

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

    def create_completed(
        self,
        analysis_id: UUID,
        user_id: UUID,
        resource_group: str,
        resources_scanned: int,
        analysis: CostAnalysis,
    ) -> AnalysisHistoryItem:
        rows = self._request(
            "POST",
            json={
                "id": str(analysis_id),
                "user_id": str(user_id),
                "resource_group": resource_group,
                "resources_scanned": resources_scanned,
                "issues_found": len(analysis.issues),
                "estimated_savings": json.dumps(
                    analysis.estimated_savings.model_dump(), separators=(",", ":")
                ),
                "analysis_result": analysis.model_dump(mode="json"),
                "status": "completed",
            },
        )
        if not isinstance(rows, list) or not rows:
            raise HTTPException(status_code=503, detail="Analysis result could not be stored")
        return AnalysisHistoryItem.model_validate(rows[0])

    def list_for_user(self) -> list[AnalysisHistoryItem]:
        rows = self._request(
            "GET",
            params={
                "select": "id,resource_group,resources_scanned,issues_found,estimated_savings,analysis_result,status,created_at",
                "order": "created_at.desc",
            },
        )
        if not isinstance(rows, list):
            raise HTTPException(status_code=503, detail="Analysis history is unavailable")
        return [AnalysisHistoryItem.model_validate(row) for row in rows]

    def _request(
        self,
        method: str,
        *,
        params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        if not self.base_url:
            raise HTTPException(status_code=503, detail="InsForge persistence is not configured")
        try:
            with httpx.Client(timeout=self.timeout_seconds, transport=self.transport) as client:
                response = client.request(
                    method,
                    f"{self.base_url}/api/database/records/analyses",
                    params=params,
                    json=json,
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "Content-Type": "application/json",
                        "Prefer": "return=representation",
                    },
                )
        except httpx.RequestError as exc:
            logger.error("InsForge analysis history request failed: {}", type(exc).__name__)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Analysis history is temporarily unavailable",
            ) from exc
        if response.status_code in {401, 403}:
            raise HTTPException(status_code=403, detail="Analysis history access denied")
        if response.is_error:
            logger.error("InsForge analysis history returned HTTP {}", response.status_code)
            raise HTTPException(status_code=503, detail="Analysis history is temporarily unavailable")
        return response.json() if response.content else None


def get_analysis_store(
    auth: AuthContext = Depends(require_auth_context),
    settings: Settings = Depends(get_settings),
) -> AnalysisStore:
    return AnalysisStore(
        settings.insforge_url,
        auth.access_token,
        settings.insforge_timeout_seconds,
    )
