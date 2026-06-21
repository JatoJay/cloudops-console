from typing import Any

from app.ai.confidence import ConfidenceEngine
from app.ai.fix_recommendation import FixRecommendationEngine
from app.ai.llm_client import LLMClient
from app.ai.prompt_builder import PromptBuilder
from app.ai.root_cause_analyzer import RootCauseAnalyzer
from app.core.config import Settings, get_settings
from app.models.diagnosis import Diagnosis


class AIKubernetesAgent:
    """Coordinate prompt building, LLM reasoning, and output calibration."""

    def __init__(
        self,
        prompt_builder: PromptBuilder,
        llm_client: LLMClient,
        root_cause_analyzer: RootCauseAnalyzer,
        fix_engine: FixRecommendationEngine,
        confidence_engine: ConfidenceEngine,
    ) -> None:
        self.prompt_builder = prompt_builder
        self.llm_client = llm_client
        self.root_cause_analyzer = root_cause_analyzer
        self.fix_engine = fix_engine
        self.confidence_engine = confidence_engine

    async def diagnose(self, investigation: dict[str, Any]) -> Diagnosis:
        messages = self.prompt_builder.build_messages(investigation)
        completion = await self.llm_client.complete(
            messages,
            self.root_cause_analyzer.response_schema(),
        )
        draft = self.root_cause_analyzer.analyze(completion)
        fix, commands, prevention = self.fix_engine.refine(draft)
        confidence, confidence_reasoning = self.confidence_engine.calculate(draft, investigation)

        return Diagnosis(
            root_cause=draft.root_cause.strip(),
            explanation=draft.explanation.strip(),
            fix=fix,
            kubectl_commands=commands,
            prevention_recommendation=prevention,
            confidence=confidence,
            confidence_reasoning=confidence_reasoning,
        )

    @classmethod
    def from_settings(cls, settings: Settings) -> "AIKubernetesAgent":
        return cls(
            prompt_builder=PromptBuilder(),
            llm_client=LLMClient(
                api_key=settings.openrouter_api_key,
                model=settings.openrouter_model,
                base_url=settings.openrouter_base_url,
                timeout_seconds=settings.openrouter_timeout_seconds,
                max_retries=settings.openrouter_max_retries,
                max_tokens=settings.openrouter_max_tokens,
            ),
            root_cause_analyzer=RootCauseAnalyzer(),
            fix_engine=FixRecommendationEngine(),
            confidence_engine=ConfidenceEngine(),
        )


def get_ai_agent() -> AIKubernetesAgent:
    return AIKubernetesAgent.from_settings(get_settings())
