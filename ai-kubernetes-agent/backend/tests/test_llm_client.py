import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.ai.llm_client import LLMClient, LLMClientError


DIAGNOSIS = {
    "root_cause": "DATABASE_URL is missing",
    "explanation": "The container exits during startup.",
    "suggested_fix": "Add the required environment variable.",
    "kubectl_commands": ["kubectl set env deployment/api DATABASE_URL=<value> -n default"],
    "prevention_recommendation": "Validate configuration before rollout.",
    "confidence": 92,
    "confidence_reasoning": ["Logs and pod state correlate"],
}


@pytest.mark.anyio
async def test_llm_client_sends_structured_request_and_parses_json() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert request.headers["Authorization"] == "Bearer test-key"
        assert body["response_format"]["type"] == "json_schema"
        assert body["temperature"] == 0.1
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(DIAGNOSIS)}}]},
        )

    client = LLMClient(
        api_key="test-key",
        model="openai/test-model",
        transport=httpx.MockTransport(handler),
    )

    result = await client.complete([{"role": "user", "content": "evidence"}], {"type": "object"})

    assert result == DIAGNOSIS


@pytest.mark.anyio
async def test_llm_client_retries_transient_failures() -> None:
    attempts = 0

    async def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(DIAGNOSIS)}}]},
        )

    client = LLMClient(
        api_key="test-key",
        model="openai/test-model",
        max_retries=1,
        transport=httpx.MockTransport(handler),
    )

    with patch.object(client, "_backoff", new=AsyncMock()):
        result = await client.complete([], {"type": "object"})

    assert attempts == 2
    assert result["confidence"] == 92


@pytest.mark.anyio
async def test_llm_client_reports_missing_configuration_without_exposing_secrets() -> None:
    client = LLMClient(api_key="", model="")

    with pytest.raises(LLMClientError, match="OPENROUTER_API_KEY"):
        await client.complete([], {"type": "object"})
