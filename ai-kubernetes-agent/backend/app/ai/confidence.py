from typing import Any

from app.ai.root_cause_analyzer import DiagnosisDraft


class ConfidenceEngine:
    """Calibrate model confidence against the amount of corroborating evidence."""

    def calculate(
        self,
        draft: DiagnosisDraft,
        investigation: dict[str, Any],
    ) -> tuple[int, list[str]]:
        signals = self._signal_sources(investigation)
        score = draft.confidence

        if not signals:
            score = min(score, 20)
        elif len(signals) == 1:
            score = min(score, 70)
        elif len(signals) == 2:
            score = min(score, 90)

        reasons = [reason.strip() for reason in draft.confidence_reasoning if reason.strip()]
        reasons.append(
            f"Corroborating evidence was available from {len(signals)} source(s): "
            f"{', '.join(signals) if signals else 'none'}"
        )
        return max(0, min(100, score)), reasons[:8]

    @staticmethod
    def _signal_sources(investigation: dict[str, Any]) -> list[str]:
        checks = {
            "pods": investigation.get("pods", {}).get("problematic_pods"),
            "logs": investigation.get("logs", {}).get("findings"),
            "events": investigation.get("events", {}).get("findings"),
            "deployments": investigation.get("deployments", {}).get("unhealthy_deployments"),
            "network": investigation.get("network", {}).get("issues"),
        }
        return [name for name, value in checks.items() if value]
