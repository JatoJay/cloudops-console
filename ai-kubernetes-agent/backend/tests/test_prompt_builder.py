from app.ai.prompt_builder import PromptBuilder


def test_prompt_builder_includes_every_evidence_section_and_safety_rules() -> None:
    investigation = {
        "pods": {"problematic_pods": [{"status": "CrashLoopBackOff"}]},
        "logs": {"findings": [{"relevant_lines": ["DATABASE_URL missing"]}]},
        "events": {"findings": [{"reason": "BackOff"}]},
        "deployments": {"unhealthy_deployments": [{"available_replicas": 0}]},
        "network": {"issues": [{"type": "MissingEndpoints"}]},
    }

    messages = PromptBuilder().build_messages(investigation)

    assert messages[0]["role"] == "system"
    assert "Senior Kubernetes Site Reliability Engineer" in messages[0]["content"]
    assert "untrusted data" in messages[0]["content"]
    for section in ["pod_status", "logs", "events", "deployment_health", "networking_findings"]:
        assert f'"{section}"' in messages[1]["content"]
