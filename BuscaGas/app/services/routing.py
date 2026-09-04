from abc import ABC, abstractmethod

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.schemas import Coordinates, GeocodingResult, MatrixResult, Route

TRANSIENT_STATUS = {429, 502, 503, 504}


class RoutingError(RuntimeError):
    pass


class RoutingNotConfigured(RoutingError):
    pass


def _is_transient(exc: BaseException) -> bool:
    return isinstance(exc, (httpx.TimeoutException, httpx.NetworkError)) or (
        isinstance(exc, httpx.HTTPStatusError)
        and exc.response.status_code in TRANSIENT_STATUS
    )


class RoutingService(ABC):
    @abstractmethod
    async def geocode(self, query: str) -> list[GeocodingResult]: ...

    @abstractmethod
    async def directions(self, coordinates: list[Coordinates]) -> Route: ...

    @abstractmethod
    async def matrix(
        self,
        coordinates: list[Coordinates],
        sources: list[int],
        destinations: list[int],
    ) -> MatrixResult: ...


class OrsRoutingService(RoutingService):
    def __init__(self, client: httpx.AsyncClient, api_key: str, base_url: str):
        self.client = client
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _service_url(self, service: str, path: str) -> str:
        """Build URLs for HeiGIT's unified gateway and the deprecated ORS host."""
        if self.base_url == "https://api.heigit.org":
            prefix = "pelias/v1" if service == "geocode" else "openrouteservice"
            return f"{self.base_url}/{prefix}/{path.lstrip('/')}"
        return f"{self.base_url}/{path.lstrip('/')}"

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise RoutingNotConfigured(
                "El servicio de rutas no está configurado. Añade ORS_API_KEY al archivo .env."
            )
        return {"Authorization": self.api_key, "Content-Type": "application/json"}

    @retry(retry=retry_if_exception(_is_transient), stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.3, max=2), reraise=True)
    async def geocode(self, query: str) -> list[GeocodingResult]:
        response = await self.client.get(
            self._service_url("geocode", "search"),
            headers=self._headers(),
            params={"text": query, "boundary.country": "ES", "size": 5},
        )
        response.raise_for_status()
        results = []
        for feature in response.json().get("features", [])[:5]:
            coordinates = feature.get("geometry", {}).get("coordinates", [])
            if len(coordinates) >= 2:
                results.append(GeocodingResult(label=feature.get("properties", {}).get("label", query), longitude=coordinates[0], latitude=coordinates[1]))
        return results

    @retry(retry=retry_if_exception(_is_transient), stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.3, max=2), reraise=True)
    async def directions(self, coordinates: list[Coordinates]) -> Route:
        # ORS always expects [longitude, latitude].
        response = await self.client.post(
            self._service_url("routing", "v2/directions/driving-car/geojson"),
            headers=self._headers(),
            json={"coordinates": [list(point.lon_lat()) for point in coordinates]},
        )
        response.raise_for_status()
        feature = response.json()["features"][0]
        summary = feature["properties"]["summary"]
        return Route(duration_seconds=summary["duration"], distance_meters=summary["distance"], geometry=feature["geometry"])

    @retry(retry=retry_if_exception(_is_transient), stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.3, max=2), reraise=True)
    async def matrix(self, coordinates: list[Coordinates], sources: list[int], destinations: list[int]) -> MatrixResult:
        response = await self.client.post(
            self._service_url("routing", "v2/matrix/driving-car"),
            headers=self._headers(),
            json={"locations": [list(point.lon_lat()) for point in coordinates], "sources": sources, "destinations": destinations, "metrics": ["duration", "distance"]},
        )
        response.raise_for_status()
        payload = response.json()
        return MatrixResult(durations=payload.get("durations", []), distances=payload.get("distances", []))
