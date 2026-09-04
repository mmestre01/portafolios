import asyncio
import logging
from datetime import UTC, datetime

import httpx
from cachetools import TTLCache
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.schemas import FUEL_FIELDS, GasStation

logger = logging.getLogger(__name__)
TRANSIENT_STATUS = {429, 502, 503, 504}


def parse_decimal(value: str | None) -> float | None:
    if value is None:
        return None
    cleaned = str(value).strip().replace(",", ".")
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except (TypeError, ValueError):
        return None


def normalize_station(raw: dict) -> GasStation | None:
    latitude = parse_decimal(raw.get("Latitud"))
    longitude = parse_decimal(raw.get("Longitud (WGS84)"))
    if latitude is None or longitude is None:
        return None
    prices = {
        key: price
        for key, field in FUEL_FIELDS.items()
        if (price := parse_decimal(raw.get(field))) is not None
    }
    try:
        return GasStation(
            id=str(raw.get("IDEESS") or f"{latitude},{longitude}"),
            name=(raw.get("Rótulo") or "Gasolinera").strip(),
            address=(raw.get("Dirección") or "").strip(),
            municipality=(raw.get("Municipio") or None),
            province=(raw.get("Provincia") or None),
            latitude=latitude,
            longitude=longitude,
            prices=prices,
        )
    except ValueError:
        return None


def _is_transient(exc: BaseException) -> bool:
    return isinstance(exc, (httpx.TimeoutException, httpx.NetworkError)) or (
        isinstance(exc, httpx.HTTPStatusError)
        and exc.response.status_code in TRANSIENT_STATUS
    )


class MitecoService:
    def __init__(self, client: httpx.AsyncClient, url: str, ttl: int = 600):
        self.client = client
        self.url = url
        self.cache: TTLCache = TTLCache(maxsize=1, ttl=ttl)
        self.lock = asyncio.Lock()
        self.last_updated: datetime | None = None
        self._stale: list[GasStation] | None = None

    @retry(
        retry=retry_if_exception(_is_transient),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.3, max=2),
        reraise=True,
    )
    async def _download(self) -> tuple[list[GasStation], str | None]:
        response = await self.client.get(self.url)
        response.raise_for_status()
        payload = response.json()
        stations = [
            station
            for raw in payload.get("ListaEESSPrecio", [])
            if (station := normalize_station(raw)) is not None
        ]
        return stations, payload.get("Fecha")

    async def get_stations(self) -> tuple[list[GasStation], str | None]:
        if "stations" in self.cache:
            return self.cache["stations"]
        async with self.lock:
            if "stations" in self.cache:
                return self.cache["stations"]
            try:
                value = await self._download()
                self.cache["stations"] = value
                self._stale = value[0]
                self.last_updated = datetime.now(UTC)
                return value
            except Exception:
                if self._stale is not None:
                    logger.warning("MITECO no disponible; se usa la última copia en memoria")
                    return self._stale, self.last_updated.isoformat() if self.last_updated else None
                raise
