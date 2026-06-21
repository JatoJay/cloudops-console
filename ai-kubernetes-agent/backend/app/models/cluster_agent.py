from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class PairingTokenRequest(BaseModel):
    cluster_name: str = Field(min_length=1, max_length=120)


class PairingTokenResponse(BaseModel):
    token: str
    expires_at: datetime
    helm_command: str
    cli_command: str


class AgentPairRequest(BaseModel):
    token: str = Field(min_length=32)
    cluster_name: str = Field(min_length=1, max_length=120)


class AgentPairResponse(BaseModel):
    cluster_id: UUID


class ClusterJobRequest(BaseModel):
    job_type: Literal["investigate", "vulnerability_scan"]
    payload: dict[str, Any] = Field(default_factory=dict)


class ConnectedCluster(BaseModel):
    id: UUID
    name: str
    provider: str
    status: str
    last_seen: datetime | None = None
    created_at: datetime


class ClusterJob(BaseModel):
    id: UUID
    cluster_id: UUID
    job_type: str
    status: str
    payload: dict[str, Any]
    progress: list[dict[str, Any]]
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime
