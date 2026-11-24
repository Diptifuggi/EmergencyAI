from __future__ import annotations

import asyncio
import math
import time
from collections import OrderedDict
from urllib.parse import urlparse
from typing import Any

import httpx

from ..core.config import settings
from ..core.logger import get_logger

logger = get_logger("app.services.location_service")

_CACHE_LIMIT = 4096
_cache: OrderedDict[tuple[str, float, float], tuple[float, str | None]] = OrderedDict()
_cache_lock = asyncio.Lock()
_request_lock = asyncio.Lock()
_last_public_request_at = 0.0


def _address_from_payload(payload: dict[str, Any]) -> str | None:
    address = payload.get("address")
    if isinstance(address, dict):
        groups = (
            ("road", "pedestrian", "footway"),
            ("neighbourhood", "suburb", "quarter", "city_district"),
            ("city", "town", "village", "municipality", "hamlet"),
            ("county", "district"),
            ("state", "state_district"),
            ("postcode",),
            ("country",),
        )
        components: list[str] = []
        seen: set[str] = set()
        house_number = address.get("house_number")
        if isinstance(house_number, str) and house_number.strip():
            components.append(house_number.strip())
            seen.add(house_number.strip().casefold())
        for group in groups:
            for key in group:
                value = address.get(key)
                if isinstance(value, str) and value.strip():
                    cleaned = value.strip()
                    normalized = cleaned.casefold()
                    if normalized not in seen:
                        components.append(cleaned)
                        seen.add(normalized)
                    break
        if components:
            return ", ".join(components)

    display_name = payload.get("display_name")
    return display_name.strip() if isinstance(display_name, str) and display_name.strip() else None


async def _cached_address(key: tuple[str, float, float]) -> tuple[bool, str | None]:
    async with _cache_lock:
        cached = _cache.get(key)
        if cached is None:
            return False, None
        expires_at, address = cached
        if expires_at <= time.monotonic():
            del _cache[key]
            return False, None
        _cache.move_to_end(key)
        return True, address


async def _store_address(
    key: tuple[str, float, float],
    address: str | None,
) -> None:
    ttl = (
        settings.NOMINATIM_CACHE_TTL_SECONDS
        if address
        else settings.NOMINATIM_FAILURE_CACHE_TTL_SECONDS
    )
    async with _cache_lock:
        _cache[key] = (time.monotonic() + ttl, address)
        _cache.move_to_end(key)
        while len(_cache) > _CACHE_LIMIT:
            _cache.popitem(last=False)


async def clear_reverse_geocode_cache() -> None:
    async with _cache_lock:
        _cache.clear()


async def reverse_geocode(latitude: float, longitude: float) -> str | None:
    """Resolve coordinates using the configured Nominatim-compatible service."""
    if (
        not isinstance(latitude, (int, float))
        or not isinstance(longitude, (int, float))
        or not math.isfinite(latitude)
        or not math.isfinite(longitude)
        or not (-90 <= latitude <= 90)
        or not (-180 <= longitude <= 180)
    ):
        logger.warning("Reverse geocoding skipped invalid coordinates")
        return None

    base_url = settings.NOMINATIM_URL.rstrip("/")
    parsed_url = urlparse(base_url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        logger.error("Reverse geocoding skipped invalid provider URL")
        return None

    key = (base_url, round(float(latitude), 6), round(float(longitude), 6))
    cached, address = await _cached_address(key)
    if cached:
        return address

    global _last_public_request_at
    is_public_nominatim = parsed_url.hostname == "nominatim.openstreetmap.org"
    async with _request_lock:
        cached, address = await _cached_address(key)
        if cached:
            return address
        if is_public_nominatim:
            delay = (
                max(1.0, settings.NOMINATIM_PUBLIC_MIN_INTERVAL_SECONDS)
                - (time.monotonic() - _last_public_request_at)
            )
            if delay > 0:
                await asyncio.sleep(delay)
            _last_public_request_at = time.monotonic()

        try:
            async with httpx.AsyncClient(
                timeout=settings.NOMINATIM_TIMEOUT_SECONDS
            ) as client:
                response = await client.get(
                    f"{base_url}/reverse",
                    params={
                        "lat": latitude,
                        "lon": longitude,
                        "format": "jsonv2",
                        "addressdetails": 1,
                        "zoom": 18,
                        "accept-language": "en",
                    },
                    headers={"User-Agent": settings.NOMINATIM_USER_AGENT},
                )
                response.raise_for_status()
                payload = response.json()
                result = _address_from_payload(payload) if isinstance(payload, dict) else None
                await _store_address(key, result)
                if result is None:
                    logger.info("Reverse geocoder returned no address")
                return result
        except httpx.HTTPStatusError as exc:
            await _store_address(key, None)
            logger.warning(
                "Reverse geocoding unavailable status_code=%d",
                exc.response.status_code,
            )
            return None
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            await _store_address(key, None)
            logger.warning(
                "Reverse geocoding unavailable error_type=%s",
                type(exc).__name__,
            )
            return None
