from unittest.mock import AsyncMock, patch

import httpx
import pytest
import pytest_asyncio

from app.services.location_service import clear_reverse_geocode_cache, reverse_geocode


@pytest_asyncio.fixture(autouse=True)
async def reset_geocode_cache() -> None:
    await clear_reverse_geocode_cache()


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
async def test_reverse_geocode_accepts_results_outside_configured_home_country() -> None:
    response = httpx.Response(
        200,
        json={"display_name": "Somewhere", "address": {"country_code": "us"}},
        request=httpx.Request("GET", "http://localhost:8080/reverse"),
    )
    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=response)):
        assert await reverse_geocode(20.3893, 72.9106) == "Somewhere"


@pytest.mark.asyncio
async def test_reverse_geocode_builds_address_from_components_and_sends_exact_coordinates() -> None:
    response = httpx.Response(
        200,
        json={
            "display_name": "Fallback",
            "address": {
                "house_number": "12",
                "road": "Main Street",
                "suburb": "Central",
                "town": "Exampletown",
                "state": "Example State",
                "postcode": "12345",
                "country": "Example Country",
                "country_code": "xx",
            },
        },
        request=httpx.Request("GET", "http://localhost:8080/reverse"),
    )
    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=response)) as mocked_get:
        assert await reverse_geocode(12.345678, -45.678912) == (
            "12, Main Street, Central, Exampletown, Example State, 12345, Example Country"
        )

    params = mocked_get.await_args.kwargs["params"]
    assert params["lat"] == 12.345678
    assert params["lon"] == -45.678912


@pytest.mark.asyncio
async def test_reverse_geocode_caches_successes_and_empty_results() -> None:
    response = httpx.Response(
        200,
        json={"address": {"city": "Exampletown"}},
        request=httpx.Request("GET", "http://localhost:8080/reverse"),
    )
    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=response)) as mocked_get:
        assert await reverse_geocode(12.345678, -45.678912) == "Exampletown"
        assert await reverse_geocode(12.345678, -45.678912) == "Exampletown"

    mocked_get.assert_awaited_once()


@pytest.mark.asyncio
async def test_reverse_geocode_does_not_invent_address_for_empty_result() -> None:
    response = httpx.Response(
        200,
        json={"address": {}, "display_name": ""},
        request=httpx.Request("GET", "http://localhost:8080/reverse"),
    )
    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=response)):
        assert await reverse_geocode(12.345678, -45.678912) is None


@pytest.mark.asyncio
async def test_reverse_geocode_returns_none_for_invalid_coordinates_or_rate_limits() -> None:
    with patch("httpx.AsyncClient.get", new=AsyncMock()) as mocked_get:
        assert await reverse_geocode(91, 0) is None
        mocked_get.assert_not_awaited()

    response = httpx.Response(
        429,
        request=httpx.Request("GET", "http://localhost:8080/reverse"),
    )
    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=response)):
        assert await reverse_geocode(12.345678, -45.678912) is None


@pytest.mark.asyncio
async def test_reverse_geocode_fails_open_on_network_error() -> None:
    with patch(
        "httpx.AsyncClient.get",
        new=AsyncMock(side_effect=httpx.ConnectError("offline")),
    ):
        assert await reverse_geocode(20.3893, 72.9106) is None