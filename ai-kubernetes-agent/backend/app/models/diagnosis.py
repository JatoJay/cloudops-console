from pydantic import BaseModel, ConfigDict, Field


class Diagnosis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    root_cause: str
    explanation: str
    fix: str
    kubectl_commands: list[str]
    prevention_recommendation: str
    confidence: int = Field(ge=0, le=100)
    confidence_reasoning: list[str]
