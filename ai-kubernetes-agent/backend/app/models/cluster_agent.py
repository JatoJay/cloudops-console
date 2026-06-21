from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class PairingTokenRequest(BaseModel):
    cluster_name: str = Field(min_length=1, max_length=120)
    provider: Literal["kubernetes", "gcp"] = "kubernetes"


class PairingTokenResponse(BaseModel):
    token: str
    expires_at: datetime
    helm_command: str
    cli_command: str


class AgentPairRequest(BaseModel):
    token: str = Field(min_length=32)
    cluster_name: str = Field(min_length=1, max_length=120)
    provider: Literal["kubernetes", "gcp"] = "kubernetes"


class AgentPairResponse(BaseModel):
    cluster_id: UUID


class ClusterJobRequest(BaseModel):
    job_type: Literal["investigate", "vulnerability_scan", "cloud_cost_analysis"]
    payload: dict[str, Any] = Field(default_factory=dict)


class ConnectedCluster(BaseModel):
    id: UUID
    name: str
    provider: str
    status: str
    metadata: dict[str, Any] = Field(default_factory=dict)
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


class CloudProject(BaseModel):
    connection_id: UUID
    project_id: str
    display_name: str
    lifecycle_state: str = "ACTIVE"


class CloudConnectionsResponse(BaseModel):
    connections: list[ConnectedCluster]
    projects: list[CloudProject]
