import asyncio
import json
from typing import Any

import httpx
from loguru import logger


class LLMClientError(RuntimeError):
    """A safe, user-facing OpenRouter client error."""


class LLMClient:
    RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str = "https://openrouter.ai/api/v1",
        timeout_seconds: float = 45.0,
        max_retries: int = 2,
        max_tokens: int = 1_200,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.max_tokens = max_tokens
        self.transport = transport

    async def complete(
        self,
        messages: list[dict[str, str]],
        response_schema: dict[str, Any],
    ) -> dict[str, Any]:
        self._validate_configuration()
        request_body = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "seed": 7,
            "max_tokens": self.max_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "kubernetes_diagnosis",
                    "strict": True,
                    "schema": response_schema,
                },
            },
        }

        timeout = httpx.Timeout(self.timeout_seconds)
        async with httpx.AsyncClient(
            timeout=timeout,
            transport=self.transport,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://insforge.dev",
                "X-Title": "CloudOps Console",
            },
        ) as client:
            for attempt in range(self.max_retries + 1):
                try:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        json=request_body,
                    )
                except httpx.RequestError as exc:
                    if attempt < self.max_retries:
                        logger.warning(
                            "OpenRouter request failed on attempt {}/{}; retrying ({})",
                            attempt + 1,
                            self.max_retries + 1,
                            type(exc).__name__,
                        )
                        await self._backoff(attempt)
                        continue
                    logger.error("OpenRouter request failed after retries: {}", type(exc).__name__)
                    raise LLMClientError("AI reasoning service is temporarily unavailable") from exc

                if response.status_code in self.RETRYABLE_STATUS_CODES and attempt < self.max_retries:
                    logger.warning(
                        "OpenRouter returned HTTP {} on attempt {}/{}; retrying",
                        response.status_code,
                        attempt + 1,
                        self.max_retries + 1,
                    )
                    await self._backoff(attempt)
                    continue

                if response.is_error:
                    logger.error("OpenRouter returned HTTP {}", response.status_code)
                    raise LLMClientError(self._status_message(response.status_code))

                return self._parse_response(response)

        raise LLMClientError("AI reasoning service is temporarily unavailable")

    def _validate_configuration(self) -> None:
        if not self.api_key:
            raise LLMClientError("OPENROUTER_API_KEY is not configured")
        if not self.model:
            raise LLMClientError("OPENROUTER_MODEL is not configured")

    @staticmethod
    def _parse_response(response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
            content = payload["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ValueError("empty completion")
            return json.loads(LLMClient._strip_code_fence(content))
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            logger.error("OpenRouter returned an invalid structured response")
            raise LLMClientError("AI reasoning returned an invalid response") from exc

    @staticmethod
    def _strip_code_fence(content: str) -> str:
        value = content.strip()
        if value.startswith("```"):
            lines = value.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            return "\n".join(lines).strip()
        return value

    @staticmethod
    async def _backoff(attempt: int) -> None:
        await asyncio.sleep(0.5 * (2**attempt))

    @staticmethod
    def _status_message(status_code: int) -> str:
        if status_code == 401:
            return "OpenRouter authentication failed"
        if status_code == 402:
            return "OpenRouter credits are unavailable"
        if status_code == 429:
            return "OpenRouter rate limit was reached"
        return "AI reasoning service request failed"
