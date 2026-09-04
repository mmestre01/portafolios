import httpx
import pytest

from app.dependencies import get_optimizer, get_routing
from app.main import app
from app.schemas import GeocodingResult, RouteResult, SearchMeta, SearchResult


class FakeRouting:
    async def geocode(self, query):
        return [GeocodingResult(label=query, latitude=40, longitude=-3)]


class FakeOptimizer:
    async def find_best_stations(self, origin, destination, fuel_type, max_detour_minutes):
        return SearchResult(route=RouteResult(duration_minutes=60, distance_km=100, geometry={"type": "LineString", "coordinates": [[-3, 40], [-2, 41]]}), stations=[], meta=SearchMeta(stations_total=1, candidates_near_route=0, candidates_evaluated=0, results=0, fuel_type=fuel_type, max_detour_minutes=max_detour_minutes, fuel_data_timestamp="today"))


async def fake_routing():
    return FakeRouting()


async def fake_optimizer():
    return FakeOptimizer()


app.dependency_overrides[get_routing] = fake_routing
app.dependency_overrides[get_optimizer] = fake_optimizer


def payload(detour=10):
    return {"origin": {"label": "Madrid", "latitude": 40, "longitude": -3}, "destination": {"label": "Valencia", "latitude": 39, "longitude": 0}, "fuel_type": "diesel", "max_detour_minutes": detour}


@pytest.mark.asyncio
async def test_pages_and_api():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        assert (await client.get("/health")).json() == {"status": "ok"}
        assert (await client.get("/")).status_code == 200
        response = await client.get("/api/geocode?q=Madrid")
        assert response.json()["results"][0]["label"] == "Madrid"
        assert (await client.post("/api/search", json=payload())).status_code == 200


@pytest.mark.asyncio
async def test_detour_validation():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        assert (await client.post("/api/search", json=payload(-1))).status_code == 422
        assert (await client.post("/api/search", json=payload(50))).status_code == 422
