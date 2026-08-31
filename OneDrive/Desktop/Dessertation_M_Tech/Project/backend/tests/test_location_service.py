from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.location_service import reverse_geocode


@pytest.mark.asyncio
async def test_reverse_geocode_returns_india_display_name() -> None:
    response = httpx.Response(
        200,
        json={
            "display_name": "Vapi, Gujarat, India",
            "address": {"country_code": "in"},
        },
        request=httpx.Request("GET", "http://localhost:8080/reverse"),
    )
    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=response)):
        assert await reverse_geocode(20.3893, 72.9106) == "Vapi, Gujarat, India"


@pytest.mark.asyncio
async def test_reverse_geocode_rejects_non_india_result() -> None:
    response = httpx.Response(
        200,
        json={"display_name": "Somewhere", "address": {"country_code": "us"}},
        request=httpx.Request("GET", "http://localhost:8080/reverse"),
    )
    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=response)):
        assert await reverse_geocode(20.3893, 72.9106) is None


@pytest.mark.asyncio
async def test_reverse_geocode_fails_open_on_network_error() -> None:
    with patch(
        "httpx.AsyncClient.get",
        new=AsyncMock(side_effect=httpx.ConnectError("offline")),
    ):
        assert await reverse_geocode(20.3893, 72.9106) is None