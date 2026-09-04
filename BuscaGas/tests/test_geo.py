from app.schemas import GasStation
from app.utils.geo import corridor_km, filter_stations_near_route


def station(identifier, lat, lon):
    return GasStation(id=identifier, name="X", address="", latitude=lat, longitude=lon, prices={"diesel": 1.4})


def test_corridor_bounds_and_metric_filter():
    assert corridor_km(3) == 5
    assert corridor_km(10) == 15
    assert corridor_km(30) == 30
    route = {"type": "LineString", "coordinates": [[-3.7, 40.4], [-0.4, 39.47]]}
    result = filter_stations_near_route(route, [station("near", 40.4, -3.69), station("far", 43.0, -8.0)], 5)
    assert [item.id for item in result] == ["near"]
