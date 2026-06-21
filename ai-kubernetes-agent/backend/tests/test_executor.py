import subprocess
from unittest.mock import patch

import pytest

from app.kubernetes.executor import KubectlExecutor


def test_executor_uses_argument_list_without_shell() -> None:
    completed = subprocess.CompletedProcess(
        args=["kubectl", "get", "pods", "-A"],
        returncode=0,
        stdout="pods",
        stderr="",
    )

    with patch("app.kubernetes.executor.subprocess.run", return_value=completed) as run:
        result = KubectlExecutor(kubeconfig_path="/tmp/config").execute(["get", "pods", "-A"])

    assert result.success is True
    assert result.stdout == "pods"
    command = run.call_args.args[0]
    assert command == ["kubectl", "--kubeconfig", "/tmp/config", "get", "pods", "-A"]
    assert "shell" not in run.call_args.kwargs


def test_executor_rejects_mutating_commands() -> None:
    with pytest.raises(ValueError, match="not read-only"):
        KubectlExecutor().execute(["delete", "pod", "api"])


def test_executor_handles_missing_kubectl() -> None:
    with patch("app.kubernetes.executor.subprocess.run", side_effect=FileNotFoundError):
        result = KubectlExecutor().execute(["get", "pods"])

    assert result.success is False
    assert result.error == "kubectl executable was not found: kubectl"


def test_executor_passes_selected_context_as_global_option() -> None:
    completed = subprocess.CompletedProcess(args=[], returncode=0, stdout="{}", stderr="")
    with patch("app.kubernetes.executor.subprocess.run", return_value=completed) as run:
        KubectlExecutor(context_name="local-dev").execute(["get", "pods", "-A", "-o", "json"])

    assert run.call_args.args[0] == [
        "kubectl", "--context", "local-dev", "get", "pods", "-A", "-o", "json"
    ]


def test_executor_allows_only_read_only_config_commands() -> None:
    with pytest.raises(ValueError, match="config command is not read-only"):
        KubectlExecutor().execute(["config", "use-context", "production"])
