from typing import Any

from pydantic import BaseModel, Field, model_validator

FUEL_FIELDS = {
    "gasolina_95": "Precio Gasolina 95 E5",
    "gasolina_98": "Precio Gasolina 98 E5",
    "diesel": "Precio Gasoleo A",
    "diesel_premium": "Precio Gasoleo Premium",
}


class Coordinates(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

    def lon_lat(self) -> tuple[float, float]:
        return self.longitude, self.latitude


class Location(Coordinates):
    label: str = Field(min_length=1, max_length=200)


class GeocodingResult(Location):
    pass


class GasStation(Coordinates):
    id: str
    name: str
    address: str
    municipality: str | None = None
    province: str | None = None
    prices: dict[str, float]


class Route(BaseModel):
    duration_seconds: float
    distance_meters: float
    geometry: dict[str, Any]


class MatrixResult(BaseModel):
    durations: list[list[float | None]]
    distances: list[list[float | None]]


class SearchRequest(BaseModel):
    origin: Location
    destination: Location
    fuel_type: str
    max_detour_minutes: float = Field(ge=0, le=30)
    autonomy_km: float = Field(default=300, ge=1, le=1500)

    @model_validator(mode="after")
    def validate_request(self) -> "SearchRequest":
        if self.fuel_type not in FUEL_FIELDS:
            raise ValueError("Tipo de combustible no válido")
        if (
            abs(self.origin.latitude - self.destination.latitude) < 1e-7
            and abs(self.origin.longitude - self.destination.longitude) < 1e-7
        ):
            raise ValueError("El origen y el destino deben ser diferentes")
        return self


class StationResult(Coordinates):
    id: str
    name: str
    address: str
    municipality: str | None
    province: str | None
    price: float
    detour_minutes: float
    extra_distance_km: float
    distance_from_origin_km: float
    travel_duration_minutes: float | None = None
    travel_distance_km: float | None = None


class RouteResult(BaseModel):
    duration_minutes: float
    distance_km: float
    geometry: dict[str, Any]


class SearchMeta(BaseModel):
    stations_total: int
    candidates_near_route: int
    candidates_evaluated: int
    results: int
    fuel_type: str
    max_detour_minutes: float
    autonomy_km: float
    fuel_data_timestamp: str | None


class SearchResult(BaseModel):
    route: RouteResult
    stations: list[StationResult]
    meta: SearchMeta


class NearbySearchRequest(BaseModel):
    location: Location
    fuel_type: str
    limit_type: str
    limit_value: float = Field(gt=0, le=200)

    @model_validator(mode="after")
    def validate_request(self) -> "NearbySearchRequest":
        if self.fuel_type not in FUEL_FIELDS:
            raise ValueError("Tipo de combustible no válido")
        if self.limit_type not in {"distance", "time"}:
            raise ValueError("El límite debe indicarse por distancia o tiempo")
        if self.limit_type == "time" and self.limit_value > 120:
            raise ValueError("El tiempo máximo es de 120 minutos")
        return self


class NearbySearchMeta(BaseModel):
    stations_total: int
    candidates_evaluated: int
    results: int
    fuel_type: str
    limit_type: str
    limit_value: float
    fuel_data_timestamp: str | None


class NearbySearchResult(BaseModel):
    location: Location
    stations: list[StationResult]
    meta: NearbySearchMeta
