from datetime import datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class EstimatedSavings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    monthly: float = Field(ge=0)
    annual: float = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)


class CostIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resource_id: str
    resource_name: str
    category: Literal[
        "over_provisioning",
        "unused_or_idle",
        "misconfiguration",
        "wrong_pricing_tier",
        "cost_optimization",
    ]
    severity: Literal["high", "medium", "low"]
    finding: str
    rationale: str
    estimated_savings: EstimatedSavings
    fix_commands: list[str]


class CostAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    issues: list[CostIssue]
    estimated_savings: EstimatedSavings
    assumptions: list[str]


class AnalyzeRequest(BaseModel):
    analysis_id: UUID = Field(default_factory=uuid4)
    resource_group: str | None = None
    connection_id: UUID | None = None
    project_id: str | None = None


class CostAnalysisResponse(CostAnalysis):
    analysis_id: UUID


class AnalysisHistoryItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    resource_group: str
    resources_scanned: int
    issues_found: int
    estimated_savings: str
    analysis_result: dict[str, Any]
    status: str
    created_at: datetime
