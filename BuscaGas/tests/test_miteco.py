import httpx
import pytest

from app.services.miteco import MitecoService, normalize_station, parse_decimal


def test_parse_decimal():
    assert parse_decimal("1,459") == 1.459
    assert parse_decimal(" 40,4167 ") == 40.4167
    assert parse_decimal("") is None
    assert parse_decimal(None) is None


def test_normalization_and_invalid_coordinates():
    raw = {"IDEESS": "7", "Rótulo": "PRUEBA", "Latitud": "40,4", "Longitud (WGS84)": "-3,7", "Precio Gasoleo A": "1,399", "Precio Gasolina 95 E5": "1,499"}
    station = normalize_station(raw)
    assert station and station.prices == {"gasolina_95": 1.499, "diesel": 1.399}
    assert normalize_station({"Latitud": "rota", "Longitud (WGS84)": "-3"}) is None


@pytest.mark.asyncio
async def test_cache_avoids_second_request():
    calls = 0
    async def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"Fecha": "ahora", "ListaEESSPrecio": [{"IDEESS": "1", "Latitud": "40", "Longitud (WGS84)": "-3"}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = MitecoService(client, "https://example.test", ttl=60)
        await service.get_stations()
        await service.get_stations()
    assert calls == 1
