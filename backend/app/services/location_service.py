from __future__ import annotations

from typing import Any

import httpx

from ..core.config import settings
from ..core.logger import get_logger

logger = get_logger("app.services.location_service")


async def reverse_geocode(latitude: float, longitude: float) -> str | None:
    """Return a local Nominatim display name, or None when enrichment fails.

    Raw coordinates are authoritative. This function intentionally fails open so
    that a geocoder outage can never prevent emergency persistence.
    """
    base_url = settings.NOMINATIM_URL.rstrip("/")
    if not base_url or "nominatim.openstreetmap.org" in base_url.lower():
        logger.warning("Ignoring unsafe public Nominatim URL")
        return None

    try:
        async with httpx.AsyncClient(timeout=settings.NOMINATIM_TIMEOUT_SECONDS) as client:
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
                headers={"User-Agent": "EmergencyIQ/1.0 location-enrichment"},
            )
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
            country_code = str(payload.get("address", {}).get("country_code", "")).lower()
            if country_code and country_code != settings.NOMINATIM_COUNTRY_CODE.lower():
                logger.warning("Reverse geocoder returned non-India result: %s", country_code)
                return None
            display_name = payload.get("display_name")
            return display_name.strip() if isinstance(display_name, str) and display_name.strip() else None
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        logger.warning("Local reverse geocoding unavailable: %s", exc)
        return None