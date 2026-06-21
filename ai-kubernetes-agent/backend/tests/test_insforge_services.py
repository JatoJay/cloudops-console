from uuid import UUID

import httpx
import pytest
from fastapi import HTTPException

from app.services.insforge import InsForgeAuthService, InvestigationRunStore


@pytest.mark.anyio
async def test_auth_service_validates_bearer_session() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer user-token"
        return httpx.Response(
            200,
            json={
                "user": {
                    "id": "11111111-1111-4111-8111-111111111111",
                    "email": "operator@example.com",
                }
            },
        )

    service = InsForgeAuthService(
        "https://example.insforge.app",
        transport=httpx.MockTransport(handler),
    )

    auth = await service.authenticate("user-token")

    assert auth.user_id == UUID("11111111-1111-4111-8111-111111111111")
    assert auth.email == "operator@example.com"


@pytest.mark.anyio
async def test_auth_service_rejects_invalid_session() -> None:
    service = InsForgeAuthService(
        "https://example.insforge.app",
        transport=httpx.MockTransport(lambda _: httpx.Response(401)),
    )

    with pytest.raises(HTTPException) as error:
        await service.authenticate("invalid-token")

    assert error.value.status_code == 401


def test_run_store_uses_user_token_and_requires_returned_owner_row() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer user-token"
        assert request.method == "PATCH"
        return httpx.Response(200, json=[{"id": "22222222-2222-4222-8222-222222222222"}])

    store = InvestigationRunStore(
        "https://example.insforge.app",
        "user-token",
        transport=httpx.MockTransport(handler),
    )

    store.update(
        UUID("22222222-2222-4222-8222-222222222222"),
        status="running",
        current_step="checking_pods",
    )
