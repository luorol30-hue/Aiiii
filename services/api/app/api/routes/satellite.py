from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings
from app.core.errors import (
    ExternalServiceNotConfigured,
    ExternalServiceUnavailable,
    service_not_configured,
    service_unavailable,
)
from app.models import User
from app.security import get_current_user
from app.services.satellite import SatelliteClient

router = APIRouter()


class SentinelSearchRequest(BaseModel):
    bbox: list[float] = Field(min_length=4, max_length=4)
    datetime_range: str = Field(examples=["2026-08-01T00:00:00Z/2026-08-15T23:59:59Z"])
    limit: int = Field(default=10, ge=1, le=100)


@router.get("/nasa-power/daily")
async def nasa_power_daily(
    latitude: float,
    longitude: float,
    start: str,
    end: str,
    _: Annotated[User, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    parameters: str = "T2M,PRECTOTCORR,RH2M,WS2M",
) -> dict:
    requested_parameters = [item.strip() for item in parameters.split(",") if item.strip()]
    try:
        return await SatelliteClient(settings).nasa_power_daily(
            latitude, longitude, start, end, requested_parameters
        )
    except ExternalServiceNotConfigured as exc:
        raise service_not_configured(str(exc)) from exc
    except ExternalServiceUnavailable as exc:
        raise service_unavailable(str(exc)) from exc


@router.post("/sentinel/search")
async def sentinel_search(
    payload: SentinelSearchRequest,
    _: Annotated[User, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    try:
        return await SatelliteClient(settings).sentinel_search(
            payload.bbox,
            payload.datetime_range,
            payload.limit,
        )
    except ExternalServiceNotConfigured as exc:
        raise service_not_configured(str(exc)) from exc
    except ExternalServiceUnavailable as exc:
        raise service_unavailable(str(exc)) from exc
