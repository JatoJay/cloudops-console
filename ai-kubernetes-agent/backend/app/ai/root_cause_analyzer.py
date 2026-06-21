from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.ai.llm_client import LLMClientError


class DiagnosisDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    root_cause: str = Field(min_length=1, max_length=500)
    explanation: str = Field(min_length=1, max_length=2_000)
    suggested_fix: str = Field(min_length=1, max_length=2_000)
    kubectl_commands: list[str] = Field(max_length=5)
    prevention_recommendation: str = Field(min_length=1, max_length=2_000)
    confidence: int = Field(ge=0, le=100)
    confidence_reasoning: list[str] = Field(min_length=1, max_length=8)


class RootCauseAnalyzer:
    """Validate the model's correlated root-cause analysis."""

    @staticmethod
    def response_schema() -> dict[str, Any]:
        return DiagnosisDraft.model_json_schema()

    def analyze(self, completion: dict[str, Any]) -> DiagnosisDraft:
        try:
            return DiagnosisDraft.model_validate(completion)
        except ValidationError as exc:
            raise LLMClientError("AI reasoning returned an invalid diagnosis") from exc
