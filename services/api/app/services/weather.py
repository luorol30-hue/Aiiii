import httpx

from app.core.config import Settings
from app.core.errors import ExternalServiceNotConfigured, ExternalServiceUnavailable


class WeatherClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def forecast(self, latitude: float, longitude: float) -> dict:
        provider = self.settings.weather_provider.lower()
        if provider == "openweather":
            return await self._openweather(latitude, longitude)
        if provider == "tomorrow":
            return await self._tomorrow(latitude, longitude)
        if provider == "weatherapi":
            return await self._weatherapi(latitude, longitude)
        raise ExternalServiceNotConfigured(f"Unsupported WEATHER_PROVIDER: {provider}")

    async def _openweather(self, latitude: float, longitude: float) -> dict:
        if not self.settings.openweather_api_key:
            raise ExternalServiceNotConfigured("OPENWEATHER_API_KEY is not configured")
        params = {
            "lat": latitude,
            "lon": longitude,
            "appid": self.settings.openweather_api_key,
            "units": "metric",
        }
        return await self._get("https://api.openweathermap.org/data/2.5/forecast", params)

    async def _tomorrow(self, latitude: float, longitude: float) -> dict:
        if not self.settings.tomorrow_api_key:
            raise ExternalServiceNotConfigured("TOMORROW_API_KEY is not configured")
        params = {
            "location": f"{latitude},{longitude}",
            "apikey": self.settings.tomorrow_api_key,
            "timesteps": "1d",
        }
        return await self._get("https://api.tomorrow.io/v4/weather/forecast", params)

    async def _weatherapi(self, latitude: float, longitude: float) -> dict:
        if not self.settings.weatherapi_key:
            raise ExternalServiceNotConfigured("WEATHERAPI_KEY is not configured")
        params = {"q": f"{latitude},{longitude}", "key": self.settings.weatherapi_key, "days": 7}
        return await self._get("https://api.weatherapi.com/v1/forecast.json", params)

    async def _get(self, url: str, params: dict) -> dict:
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as exc:
            raise ExternalServiceUnavailable("Weather provider request failed") from exc
