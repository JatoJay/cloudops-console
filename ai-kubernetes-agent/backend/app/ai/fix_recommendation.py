import re

from app.ai.root_cause_analyzer import DiagnosisDraft


class FixRecommendationEngine:
    """Keep suggested kubectl commands reviewable and shell-free."""

    UNSAFE_SHELL_PATTERN = re.compile(r"[\n\r;|]|&&|\$\(|`")

    def refine(self, draft: DiagnosisDraft) -> tuple[str, list[str], str]:
        commands = []
        for command in draft.kubectl_commands:
            normalized = " ".join(command.strip().split())
            if not normalized.startswith("kubectl "):
                continue
            if self.UNSAFE_SHELL_PATTERN.search(normalized):
                continue
            commands.append(normalized)

        return draft.suggested_fix.strip(), commands[:5], draft.prevention_recommendation.strip()
