from dataclasses import dataclass

from app.core.config import Settings, get_settings
from app.kubernetes.executor import KubectlExecutor
from app.kubernetes.parsing import concise_error


@dataclass(frozen=True)
class ClusterContexts:
    contexts: list[str]
    current_context: str | None
    error: str | None = None


class ClusterContextService:
    """Read and validate contexts from the backend's mounted kubeconfig."""

    def __init__(self, executor: KubectlExecutor) -> None:
        self.executor = executor

    def list_contexts(self) -> ClusterContexts:
        result = self.executor.execute(["config", "get-contexts", "-o", "name"])
        if not result.success:
            detail = concise_error(result.stderr or result.error or "kubeconfig is unavailable")
            return ClusterContexts([], None, detail)

        contexts = list(dict.fromkeys(line.strip() for line in result.stdout.splitlines() if line.strip()))
        current_result = self.executor.execute(["config", "current-context"])
        current = current_result.stdout.strip() if current_result.success else None
        return ClusterContexts(contexts, current or None)

    def contains(self, context_name: str) -> bool:
        return context_name in self.list_contexts().contexts

    @classmethod
    def from_settings(cls, settings: Settings) -> "ClusterContextService":
        return cls(KubectlExecutor(settings.kubeconfig_path, timeout_seconds=settings.kubectl_timeout_seconds))


def get_cluster_context_service() -> ClusterContextService:
    return ClusterContextService.from_settings(get_settings())
