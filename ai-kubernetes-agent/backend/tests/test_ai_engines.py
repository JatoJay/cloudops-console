from app.ai.confidence import ConfidenceEngine
from app.ai.fix_recommendation import FixRecommendationEngine
from app.ai.root_cause_analyzer import DiagnosisDraft


def _draft(**overrides) -> DiagnosisDraft:
    values = {
        "root_cause": "DATABASE_URL is missing",
        "explanation": "Startup failed.",
        "suggested_fix": "Add the environment variable.",
        "kubectl_commands": [
            "kubectl set env deployment/api DATABASE_URL=<value> -n default",
            "kubectl get pods -n default && echo unsafe",
            "curl https://example.com",
        ],
        "prevention_recommendation": "Validate required configuration.",
        "confidence": 95,
        "confidence_reasoning": ["The logs name the missing variable"],
    }
    values.update(overrides)
    return DiagnosisDraft.model_validate(values)


def test_fix_engine_removes_non_kubectl_and_shell_chained_commands() -> None:
    _, commands, _ = FixRecommendationEngine().refine(_draft())

    assert commands == ["kubectl set env deployment/api DATABASE_URL=<value> -n default"]


def test_confidence_engine_caps_single_source_claims() -> None:
    investigation = {
        "pods": {"problematic_pods": [{"status": "CrashLoopBackOff"}]},
        "logs": {"findings": []},
        "events": {"findings": []},
        "deployments": {"unhealthy_deployments": []},
        "network": {"issues": []},
    }

    score, reasons = ConfidenceEngine().calculate(_draft(), investigation)

    assert score == 70
    assert reasons[-1].endswith("1 source(s): pods")
