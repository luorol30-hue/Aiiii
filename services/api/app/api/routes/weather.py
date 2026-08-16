from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.core.errors import (
    ExternalServiceNotConfigured,
    ExternalServiceUnavailable,
    service_not_configured,
    service_unavailable,
)
from app.models import User
from app.schemas import WeatherResponse
from app.security import get_current_user
from app.services.weather import WeatherClient

router = APIRouter()


@router.get("/forecast", response_model=WeatherResponse)
async def forecast(
    latitude: float,
    longitude: float,
    _: Annotated[User, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> WeatherResponse:
    try:
        payload = await WeatherClient(settings).forecast(latitude, longitude)
    except ExternalServiceNotConfigured as exc:
        raise service_not_configured(str(exc)) from exc
    except ExternalServiceUnavailable as exc:
        raise service_unavailable(str(exc)) from exc
    return WeatherResponse(
        provider=settings.weather_provider,
        latitude=latitude,
        longitude=longitude,
        payload=payload,
    )
