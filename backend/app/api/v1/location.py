from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ...core.dependencies import get_current_user
from ...core.rate_limit import sos_rate_limiter
from ...schemas.sos import ReverseGeocodeResponse
from ...schemas.v1 import UserOut
from ...services.location_service import reverse_geocode

router = APIRouter()


@router.get("/reverse", response_model=ReverseGeocodeResponse)
async def reverse_geocode_location(
    lat: float = Query(..., ge=-90.0, le=90.0),
    lon: float = Query(..., ge=-180.0, le=180.0),
    current_user: UserOut = Depends(get_current_user),
) -> ReverseGeocodeResponse:
    sos_rate_limiter.check_rate_limit(f"rev_geo_{current_user.id}", max_requests=20, window_seconds=60.0)
    address = await reverse_geocode(lat, lon)
    return ReverseGeocodeResponse(
        latitude=lat,
        longitude=lon,
        address=address,
    )
