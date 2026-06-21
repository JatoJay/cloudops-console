from typing import Any

from app.kubernetes.executor import KubectlExecutor
from app.kubernetes.parsing import parse_json_output


class NetworkInspector:
    def __init__(self, executor: KubectlExecutor) -> None:
        self.executor = executor

    def inspect(self) -> dict[str, Any]:
        services, services_error = self._get(["get", "services", "-A", "-o", "json"])
        endpoints, endpoints_error = self._get(["get", "endpoints", "-A", "-o", "json"])
        pods, pods_error = self._get(["get", "pods", "-A", "-o", "json"])
        dns_pods, dns_error = self._get(
            ["get", "pods", "-n", "kube-system", "-l", "k8s-app=kube-dns", "-o", "json"]
        )

        errors = list(
            dict.fromkeys(
                error for error in [services_error, endpoints_error, pods_error, dns_error] if error
            )
        )
        if services is None or endpoints is None or pods is None:
            return {
                "healthy": False,
                "total_services": 0,
                "issues": [],
                "dns": self._dns_status(dns_pods),
                "errors": errors,
            }

        endpoint_map = self._endpoint_map(endpoints.get("items", []))
        pod_items = pods.get("items", [])
        issues: list[dict[str, str]] = []
        service_items = services.get("items", [])

        if not service_items:
            issues.append(
                {
                    "type": "NoServices",
                    "service": "*",
                    "namespace": "*",
                    "detail": "No Kubernetes services were found",
                }
            )

        for service in service_items:
            metadata = service.get("metadata", {})
            spec = service.get("spec", {})
            name = metadata.get("name", "unknown")
            namespace = metadata.get("namespace", "default")
            selector = spec.get("selector", {})

            if spec.get("type") == "ExternalName" or not selector:
                continue

            matching_pods = self._matching_pods(pod_items, namespace, selector)
            endpoint_count = endpoint_map.get((namespace, name), 0)

            if not matching_pods:
                issues.append(
                    {
                        "type": "SelectorMismatch",
                        "service": name,
                        "namespace": namespace,
                        "detail": "No pods match the service selector",
                    }
                )
            elif endpoint_count == 0:
                issues.append(
                    {
                        "type": "MissingEndpoints",
                        "service": name,
                        "namespace": namespace,
                        "detail": "Matching pods exist but the service has no ready endpoints",
                    }
                )

        dns = self._dns_status(dns_pods)
        if not dns["healthy"]:
            issues.append(
                {
                    "type": "DNSUnavailable",
                    "service": "cluster-dns",
                    "namespace": "kube-system",
                    "detail": dns["detail"],
                }
            )

        return {
            "healthy": not issues and not errors,
            "total_services": len(service_items),
            "issues": issues,
            "dns": dns,
            "errors": errors,
        }

    def _get(self, arguments: list[str]) -> tuple[dict[str, Any] | None, str | None]:
        return parse_json_output(self.executor.execute(arguments))

    @staticmethod
    def _endpoint_map(items: list[dict[str, Any]]) -> dict[tuple[str, str], int]:
        endpoints: dict[tuple[str, str], int] = {}
        for endpoint in items:
            metadata = endpoint.get("metadata", {})
            count = sum(len(subset.get("addresses", [])) for subset in endpoint.get("subsets", []))
            endpoints[(metadata.get("namespace", "default"), metadata.get("name", "unknown"))] = count
        return endpoints

    @staticmethod
    def _matching_pods(
        pods: list[dict[str, Any]], namespace: str, selector: dict[str, str]
    ) -> list[dict[str, Any]]:
        return [
            pod
            for pod in pods
            if pod.get("metadata", {}).get("namespace", "default") == namespace
            and all(pod.get("metadata", {}).get("labels", {}).get(key) == value for key, value in selector.items())
        ]

    @staticmethod
    def _dns_status(payload: dict[str, Any] | None) -> dict[str, Any]:
        if payload is None:
            return {"healthy": False, "ready_pods": 0, "detail": "DNS pods could not be inspected"}

        items = payload.get("items", [])
        ready_count = 0
        for pod in items:
            statuses = pod.get("status", {}).get("containerStatuses", [])
            if pod.get("status", {}).get("phase") == "Running" and statuses and all(
                status.get("ready", False) for status in statuses
            ):
                ready_count += 1

        healthy = ready_count > 0
        return {
            "healthy": healthy,
            "ready_pods": ready_count,
            "detail": "Cluster DNS is ready" if healthy else "No ready cluster DNS pods were found",
        }
