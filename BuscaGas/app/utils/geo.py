from collections.abc import Iterable

from pyproj import CRS, Transformer
from shapely.geometry import LineString, Point
from shapely.ops import transform

from app.schemas import GasStation


def corridor_km(max_detour_minutes: float) -> float:
    return min(30.0, max(5.0, max_detour_minutes * 1.5))


def filter_stations_near_route(
    geometry: dict, stations: Iterable[GasStation], radius_km: float
) -> list[GasStation]:
    coordinates = geometry.get("coordinates", [])
    if len(coordinates) < 2:
        return []
    line = LineString(coordinates)
    center = line.centroid
    zone = max(1, min(60, int((center.x + 180) // 6) + 1))
    epsg = 32600 + zone if center.y >= 0 else 32700 + zone
    transformer = Transformer.from_crs(CRS.from_epsg(4326), CRS.from_epsg(epsg), always_xy=True)
    metric_line = transform(transformer.transform, line)
    corridor = metric_line.buffer(radius_km * 1000)
    nearby_with_distance = []
    for station in stations:
        point = Point(*transformer.transform(station.longitude, station.latitude))
        if corridor.covers(point):
            nearby_with_distance.append((metric_line.distance(point), station))
    nearby_with_distance.sort(key=lambda item: item[0])
    return [station for _, station in nearby_with_distance]
