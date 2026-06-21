import json
from pathlib import Path

from app.cluster_agent import write_in_cluster_kubeconfig
from app.cloud_agent import GCPConnector
from app.services.cluster_agents import hash_agent_secret


def test_agent_secret_hash_is_deterministic_and_not_plaintext() -> None:
    token = "coa_example-secret"
    digest = hash_agent_secret(token)
    assert digest == hash_agent_secret(token)
    assert token not in digest
    assert len(digest) == 64


def test_in_cluster_kubeconfig_uses_service_account_token_file(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("KUBERNETES_SERVICE_HOST", "10.0.0.1")
    monkeypatch.setenv("KUBERNETES_SERVICE_PORT_HTTPS", "6443")
    target = tmp_path / "config"

    assert write_in_cluster_kubeconfig(str(target)) == str(target)
    config = json.loads(target.read_text())
    assert config["clusters"][0]["cluster"]["server"] == "https://10.0.0.1:6443"
    assert config["users"][0]["user"]["tokenFile"].endswith("/serviceaccount/token")
    assert "token" not in config["users"][0]["user"]


def test_gcp_connector_lists_only_normalized_projects(monkeypatch) -> None:
    class Result:
        returncode = 0
        stderr = ""
        stdout = json.dumps([
            {"projectId": "prod-123", "name": "Production", "lifecycleState": "ACTIVE"},
            {"name": "Missing ID"},
        ])

    monkeypatch.setattr("app.cloud_agent.subprocess.run", lambda *args, **kwargs: Result())
    projects = GCPConnector("https://example.com", "coa_token", "GCP").projects()
    assert projects == [{
        "project_id": "prod-123",
        "display_name": "Production",
        "lifecycle_state": "ACTIVE",
    }]
