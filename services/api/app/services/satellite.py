import httpx

from app.core.config import Settings
from app.core.errors import ExternalServiceNotConfigured, ExternalServiceUnavailable


class SatelliteClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def nasa_power_daily(
        self,
        latitude: float,
        longitude: float,
        start: str,
        end: str,
        parameters: list[str],
    ) -> dict:
        params = {
            "community": "AG",
            "latitude": latitude,
            "longitude": longitude,
            "start": start,
            "end": end,
            "parameters": ",".join(parameters),
            "format": "JSON",
        }
        return await self._get("https://power.larc.nasa.gov/api/temporal/daily/point", params)

    async def sentinel_search(self, bbox: list[float], datetime_range: str, limit: int) -> dict:
        if not self.settings.sentinelhub_client_id or not self.settings.sentinelhub_client_secret:
            raise ExternalServiceNotConfigured("Sentinel Hub OAuth credentials are not configured")
        token = await self._sentinel_token()
        payload = {
            "bbox": bbox,
            "datetime": datetime_range,
            "collections": ["sentinel-2-l2a"],
            "limit": limit,
        }
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    "https://services.sentinel-hub.com/api/v1/catalog/1.0.0/search",
                    json=payload,
                    headers={"Authorization": f"Bearer {token}"},
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as exc:
            raise ExternalServiceUnavailable("Sentinel Hub catalog request failed") from exc

    async def _sentinel_token(self) -> str:
        data = {
            "grant_type": "client_credentials",
            "client_id": self.settings.sentinelhub_client_id,
            "client_secret": self.settings.sentinelhub_client_secret,
        }
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(
                    "https://services.sentinel-hub.com/auth/realms/main/protocol/openid-connect/token",
                    data=data,
                )
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:
            raise ExternalServiceUnavailable("Sentinel Hub OAuth request failed") from exc
        return payload["access_token"]

    async def _get(self, url: str, params: dict) -> dict:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as exc:
            raise ExternalServiceUnavailable("Satellite provider request failed") from exc
