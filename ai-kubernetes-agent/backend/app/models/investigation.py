from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.diagnosis import Diagnosis


class InvestigationEvidence(BaseModel):
    pods: dict[str, Any]
    logs: dict[str, Any]
    events: dict[str, Any]
    deployments: dict[str, Any]
    network: dict[str, Any]


class InvestigationResponse(BaseModel):
    investigation_id: UUID
    status: Literal["success", "partial"]
    investigation: InvestigationEvidence
    diagnosis: Diagnosis | None = None
    errors: list[str] = Field(default_factory=list)
    message: str | None = None
    guidance: list[str] = Field(default_factory=list)
    cluster_healthy: bool = False


class InvestigationRequest(BaseModel):
    investigation_id: UUID | None = None
    namespace: str = Field(default="all", min_length=1, max_length=253)
    context: str | None = Field(default=None, min_length=1, max_length=512)
