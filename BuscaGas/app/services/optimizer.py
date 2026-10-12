import logging
import time

from app.schemas import (
    Coordinates,
    Location,
    NearbySearchMeta,
    NearbySearchResult,
    RouteResult,
    SearchMeta,
    SearchResult,
    StationResult,
)
from app.services.miteco import MitecoService
from app.services.routing import RoutingService
from app.utils.geo import corridor_km, distance_km, filter_stations_near_route

logger = logging.getLogger(__name__)


class StationOptimizer:
    def __init__(
        self,
        routing: RoutingService,
        miteco: MitecoService,
        batch_size: int = 40,
        max_results: int = 20,
        max_candidates: int = 200,
    ):
        self.routing = routing
        self.miteco = miteco
        self.batch_size = batch_size
        self.max_results = max_results
        self.max_candidates = max_candidates

    async def find_nearby_stations(
        self, location: Location, fuel_type: str, limit_type: str, limit_value: float
    ) -> NearbySearchResult:
        stations, timestamp = await self.miteco.get_stations()
        # Driving distance is never shorter than straight-line distance. For a time
        # search, 2.2 km/min keeps motorway candidates while bounding Matrix usage.
        radius = limit_value if limit_type == "distance" else limit_value * 2.2
        candidates = [
            (distance_km(location.latitude, location.longitude, station.latitude, station.longitude), station)
            for station in stations
            if fuel_type in station.prices
        ]
        candidates = sorted((item for item in candidates if item[0] <= radius), key=lambda item: item[0])[
            : self.max_candidates
        ]
        evaluated = []
        for offset in range(0, len(candidates), self.batch_size):
            batch = candidates[offset : offset + self.batch_size]
            points = [
                location,
                *[Coordinates(latitude=item[1].latitude, longitude=item[1].longitude) for item in batch],
            ]
            matrix = await self.routing.matrix(points, [0], list(range(1, len(points))))
            durations = matrix.durations[0] if matrix.durations else []
            distances = matrix.distances[0] if matrix.distances else []
            for index, (_, station) in enumerate(batch):
                if index >= len(durations) or index >= len(distances):
                    continue
                if durations[index] is None or distances[index] is None:
                    continue
                travel_minutes = durations[index] / 60
                travel_km = distances[index] / 1000
                measure = travel_km if limit_type == "distance" else travel_minutes
                if measure <= limit_value + 1e-6:
                    evaluated.append((station, travel_minutes, travel_km))
        evaluated.sort(key=lambda item: (item[0].prices[fuel_type], item[1]))
        results = [
            StationResult(
                id=station.id,
                name=station.name,
                address=station.address,
                municipality=station.municipality,
                province=station.province,
                latitude=station.latitude,
                longitude=station.longitude,
                price=station.prices[fuel_type],
                detour_minutes=0,
                extra_distance_km=0,
                distance_from_origin_km=travel_km,
                travel_duration_minutes=travel_minutes,
                travel_distance_km=travel_km,
                prices=station.prices,
                schedule=station.schedule,
                sale_type=station.sale_type,
            )
            for station, travel_minutes, travel_km in evaluated[: self.max_results]
        ]
        return NearbySearchResult(
            location=location,
            stations=results,
            meta=NearbySearchMeta(
                stations_total=len(stations),
                candidates_evaluated=len(candidates),
                results=len(results),
                fuel_type=fuel_type,
                limit_type=limit_type,
                limit_value=limit_value,
                fuel_data_timestamp=timestamp,
            ),
        )

    async def _evaluate_batch(self, origin, destination, stations, base_route, fuel_type):
        station_coords = [Coordinates(latitude=s.latitude, longitude=s.longitude) for s in stations]
        points = [origin, *station_coords, destination]
        station_indexes = list(range(1, len(stations) + 1))
        destination_index = len(points) - 1
        outbound = await self.routing.matrix(points, [0], station_indexes)
        onward = await self.routing.matrix(points, station_indexes, [destination_index])
        results = []
        for index, station in enumerate(stations):
            try:
                first_duration = outbound.durations[0][index]
                first_distance = outbound.distances[0][index]
                second_duration = onward.durations[index][0]
                second_distance = onward.distances[index][0]
            except (IndexError, TypeError):
                continue
            if None in (first_duration, first_distance, second_duration, second_distance):
                continue
            detour_seconds = max(0.0, first_duration + second_duration - base_route.duration_seconds)
            extra_meters = max(0.0, first_distance + second_distance - base_route.distance_meters)
            results.append(
                (
                    station,
                    detour_seconds,
                    extra_meters,
                    station.prices[fuel_type],
                    first_distance,
                )
            )
        return results

    async def find_best_stations(
        self,
        origin: Coordinates,
        destination: Coordinates,
        fuel_type: str,
        max_detour_minutes: float,
        autonomy_km: float = 300,
    ) -> SearchResult:
        started = time.monotonic()
        base_route = await self.routing.directions([origin, destination])
        stations, timestamp = await self.miteco.get_stations()
        with_fuel = [station for station in stations if fuel_type in station.prices]
        nearby = filter_stations_near_route(base_route.geometry, with_fuel, corridor_km(max_detour_minutes))[
            : self.max_candidates
        ]
        evaluated = []
        for offset in range(0, len(nearby), self.batch_size):
            batch = nearby[offset : offset + self.batch_size]
            evaluated.extend(await self._evaluate_batch(origin, destination, batch, base_route, fuel_type))
        maximum_seconds = max_detour_minutes * 60 + 0.5
        maximum_range_meters = autonomy_km * 1000
        valid = [item for item in evaluated if item[1] <= maximum_seconds and item[4] <= maximum_range_meters]
        valid.sort(key=lambda item: (item[3], item[1]))
        result_stations = [
            StationResult(
                id=station.id,
                name=station.name,
                address=station.address,
                municipality=station.municipality,
                province=station.province,
                latitude=station.latitude,
                longitude=station.longitude,
                price=price,
                detour_minutes=detour / 60,
                extra_distance_km=extra / 1000,
                distance_from_origin_km=distance_from_origin / 1000,
                prices=station.prices,
                schedule=station.schedule,
                sale_type=station.sale_type,
            )
            for station, detour, extra, price, distance_from_origin in valid[: self.max_results]
        ]
        logger.info(
            "search route_duration=%.1f route_distance=%.1f fuel=%s max_detour=%s stations_loaded=%d stations_with_fuel=%d stations_in_corridor=%d stations_evaluated=%d results_found=%d elapsed=%.2f",
            base_route.duration_seconds,
            base_route.distance_meters,
            fuel_type,
            max_detour_minutes,
            len(stations),
            len(with_fuel),
            len(nearby),
            len(evaluated),
            len(result_stations),
            time.monotonic() - started,
        )
        return SearchResult(
            route=RouteResult(
                duration_minutes=base_route.duration_seconds / 60,
                distance_km=base_route.distance_meters / 1000,
                geometry=base_route.geometry,
            ),
            stations=result_stations,
            meta=SearchMeta(
                stations_total=len(stations),
                candidates_near_route=len(nearby),
                candidates_evaluated=len(evaluated),
                results=len(result_stations),
                fuel_type=fuel_type,
                max_detour_minutes=max_detour_minutes,
                autonomy_km=autonomy_km,
                fuel_data_timestamp=timestamp,
            ),
        )
