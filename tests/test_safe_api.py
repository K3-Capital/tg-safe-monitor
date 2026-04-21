import httpx
import pytest

from tg_safe_monitor.safe_api import SafeApiClient


@pytest.mark.asyncio
async def test_is_safe_uses_v1_safe_details_endpoint() -> None:
    requested_urls: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        if str(request.url) == "https://api.safe.global/tx-service/eth/api/v1/safes/0xabc/":
            return httpx.Response(200, json={"address": "0xabc"})
        return httpx.Response(404, json={"detail": "Not found"})

    client = SafeApiClient(
        "https://api.safe.global/tx-service/eth/api/v2",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    try:
        assert await client.is_safe("0xabc") is True
    finally:
        await client.aclose()

    assert requested_urls == ["https://api.safe.global/tx-service/eth/api/v1/safes/0xabc/"]