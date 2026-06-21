from collections.abc import Callable
from typing import Any

from loguru import logger

from app.core.config import Settings, get_settings
from app.kubernetes import (
    DeploymentInspector,
    EventsAnalyzer,
    KubectlExecutor,
    LogsCollector,
    NetworkInspector,
    PodInspector,
)
from app.kubernetes.parsing import concise_error


class InvestigationService:
    """Collect Kubernetes evidence in a predictable troubleshooting order."""

    def __init__(
        self,
        pod_inspector: PodInspector,
        logs_collector: LogsCollector,
        events_analyzer: EventsAnalyzer,
        deployment_inspector: DeploymentInspector,
        network_inspector: NetworkInspector,
        settings: Settings | None = None,
        executor: KubectlExecutor | None = None,
    ) -> None:
        self.pod_inspector = pod_inspector
        self.logs_collector = logs_collector
        self.events_analyzer = events_analyzer
        self.deployment_inspector = deployment_inspector
        self.network_inspector = network_inspector
        self.settings = settings
        self.executor = executor

    def investigate(
        self,
        progress: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        logger.info("Starting Kubernetes evidence collection")
        self._notify(progress, "checking_pods")
        if self.executor:
            connectivity = self.executor.execute(["cluster-info", "--request-timeout=5s"])
            if not connectivity.success:
                error = concise_error(
                    connectivity.stderr or connectivity.error or "cluster is unreachable"
                )
                logger.warning("Kubernetes connectivity check failed: {}", error)
                return self._unavailable_evidence(error)
        pods = self.pod_inspector.inspect()
        self._notify(progress, "reading_logs")
        logs = self.logs_collector.collect(pods.get("problematic_pods", []))
        self._notify(progress, "analyzing_events")
        events = self.events_analyzer.analyze()
        self._notify(progress, "inspecting_deployments")
        deployments = self.deployment_inspector.inspect()
        self._notify(progress, "checking_networking")
        network = self.network_inspector.inspect()

        investigation = {
            "pods": pods,
            "logs": logs,
            "events": events,
            "deployments": deployments,
            "network": network,
        }
        logger.info("Kubernetes evidence collection finished")
        return investigation

    @staticmethod
    def _notify(progress: Callable[[str], None] | None, step: str) -> None:
        if progress:
            progress(step)

    @staticmethod
    def _unavailable_evidence(error: str) -> dict[str, Any]:
        return {
            "pods": {"healthy": False, "error": error, "total_pods": 0, "problematic_pods": []},
            "logs": {"healthy": False, "findings": [], "errors": [error], "pods_checked": 0},
            "events": {"healthy": False, "error": error, "findings": []},
            "deployments": {"healthy": False, "error": error, "total_deployments": 0, "unhealthy_deployments": []},
            "network": {"healthy": False, "total_services": 0, "issues": [], "errors": [error]},
        }

    @classmethod
    def from_settings(cls, settings: Settings, context_name: str = "") -> "InvestigationService":
        executor = KubectlExecutor(
            kubeconfig_path=settings.kubeconfig_path,
            context_name=context_name,
            timeout_seconds=settings.kubectl_timeout_seconds,
        )
        return cls(
            pod_inspector=PodInspector(
                executor,
                container_creating_timeout_seconds=settings.container_creating_timeout_seconds,
            ),
            logs_collector=LogsCollector(executor, tail_lines=settings.kubectl_log_tail_lines),
            events_analyzer=EventsAnalyzer(executor),
            deployment_inspector=DeploymentInspector(executor),
            network_inspector=NetworkInspector(executor),
            settings=settings,
            executor=executor,
        )

    def for_context(self, context_name: str) -> "InvestigationService":
        if self.settings is None:
            raise RuntimeError("This investigation service cannot select a kubeconfig context")
        return self.from_settings(self.settings, context_name=context_name)


def get_investigation_service() -> InvestigationService:
    return InvestigationService.from_settings(get_settings())
