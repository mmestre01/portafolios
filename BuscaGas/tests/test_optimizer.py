import pytest

from app.schemas import Coordinates, GasStation, Location, MatrixResult, Route
from app.services.optimizer import StationOptimizer


class FakeMiteco:
    async def get_stations(self):
        return [
            GasStation(id="A", name="A", address="", latitude=40.05, longitude=-3, prices={"diesel": 1.40}),
            GasStation(id="B", name="B", address="", latitude=40.06, longitude=-3, prices={"diesel": 1.35}),
            GasStation(id="C", name="C", address="", latitude=40.07, longitude=-3, prices={"diesel": 1.35}),
        ], "today"


class FakeRouting:
    async def directions(self, coordinates):
        return Route(
            duration_seconds=6000,
            distance_meters=100000,
            geometry={"type": "LineString", "coordinates": [[-3, 40], [-3, 41]]},
        )

    async def matrix(self, coordinates, sources, destinations):
        if sources == [0]:
            return MatrixResult(durations=[[2400, 3000, 3000]], distances=[[40000, 50000, 50000]])
        return MatrixResult(durations=[[3840], [3900], [3240]], distances=[[64000], [65000], [52000]])


@pytest.mark.asyncio
async def test_filter_by_real_detour_and_sort_price_then_detour():
    optimizer = StationOptimizer(FakeRouting(), FakeMiteco(), 40, 20)
    result = await optimizer.find_best_stations(
        Coordinates(latitude=40, longitude=-3), Coordinates(latitude=41, longitude=-3), "diesel", 10
    )
    assert [station.id for station in result.stations] == ["C", "A"]
    assert result.stations[1].detour_minutes == 4


class PartialRouting(FakeRouting):
    async def matrix(self, coordinates, sources, destinations):
        if sources == [0]:
            return MatrixResult(durations=[[2400, None, 3000]], distances=[[40000, None, 50000]])
        return MatrixResult(durations=[[3840], [3900], [3240]], distances=[[64000], [65000], [52000]])


@pytest.mark.asyncio
async def test_partial_matrix_skips_only_broken_station():
    result = await StationOptimizer(PartialRouting(), FakeMiteco()).find_best_stations(
        Coordinates(latitude=40, longitude=-3), Coordinates(latitude=41, longitude=-3), "diesel", 10
    )
    assert [station.id for station in result.stations] == ["C", "A"]


class NearbyRouting(FakeRouting):
    async def matrix(self, coordinates, sources, destinations):
        assert sources == [0]
        return MatrixResult(durations=[[480, 900, 1200]], distances=[[7000, 12000, 18000]])


@pytest.mark.asyncio
async def test_nearby_search_filters_by_driving_distance_and_sorts_by_price():
    result = await StationOptimizer(NearbyRouting(), FakeMiteco()).find_nearby_stations(
        Location(label="Mi ubicación", latitude=40, longitude=-3), "diesel", "distance", 15
    )
    assert [station.id for station in result.stations] == ["B", "A"]
    assert result.stations[0].travel_duration_minutes == 15
    assert result.stations[0].travel_distance_km == 12


@pytest.mark.asyncio
async def test_nearby_search_filters_by_driving_time():
    result = await StationOptimizer(NearbyRouting(), FakeMiteco()).find_nearby_stations(
        Location(label="Mi ubicación", latitude=40, longitude=-3), "diesel", "time", 10
    )
    assert [station.id for station in result.stations] == ["A"]
