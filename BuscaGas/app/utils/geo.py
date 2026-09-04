from collections.abc import Iterable

from pyproj import CRS, Transformer
from shapely.geometry import LineString, Point
from shapely.ops import transform

from app.schemas import GasStation


def distance_km(first_lat: float, first_lon: float, second_lat: float, second_lon: float) -> float:
    """Return the geodesic distance between two WGS84 points in kilometres."""
    from math import asin, cos, radians, sin, sqrt

    lat1, lat2 = radians(first_lat), radians(second_lat)
    delta_lat = lat2 - lat1
    delta_lon = radians(second_lon - first_lon)
    value = sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
    return 6371.0088 * 2 * asin(sqrt(value))


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
