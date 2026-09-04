import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import get_settings
from app.dependencies import get_optimizer, get_routing
from app.schemas import NearbySearchRequest, NearbySearchResult, SearchRequest, SearchResult
from app.services.miteco import MitecoService
from app.services.optimizer import StationOptimizer
from app.services.routing import OrsRoutingService, RoutingNotConfigured, RoutingService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
settings = get_settings()
templates = Jinja2Templates(directory="app/templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = httpx.AsyncClient(timeout=settings.http_timeout_seconds, follow_redirects=True)
    routing = OrsRoutingService(client, settings.ors_api_key, settings.ors_base_url)
    miteco = MitecoService(client, settings.miteco_stations_url, settings.stations_cache_ttl)
    app.state.routing = routing
    app.state.optimizer = StationOptimizer(
        routing,
        miteco,
        settings.matrix_batch_size,
        settings.max_results,
        settings.max_matrix_candidates,
    )
    yield
    await client.aclose()


app = FastAPI(title="BuscaGas", version="1.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/geocode")
async def geocode(
    q: str = Query(min_length=2, max_length=200),
    routing: RoutingService = Depends(get_routing),
):
    try:
        return {"results": await routing.geocode(q.strip())}
    except RoutingNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=503, detail="No se ha podido consultar el buscador de lugares."
        ) from exc


@app.post("/api/search", response_model=SearchResult)
async def search(payload: SearchRequest, optimizer: StationOptimizer = Depends(get_optimizer)):
    try:
        return await optimizer.find_best_stations(
            payload.origin,
            payload.destination,
            payload.fuel_type,
            payload.max_detour_minutes,
            payload.autonomy_km,
        )
    except RoutingNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        logging.getLogger(__name__).error("External service failure: %s", type(exc).__name__)
        raise HTTPException(
            status_code=503,
            detail="No se ha podido calcular la ruta o consultar los precios. Inténtalo de nuevo.",
        ) from exc


@app.post("/api/nearby", response_model=NearbySearchResult)
async def nearby(payload: NearbySearchRequest, optimizer: StationOptimizer = Depends(get_optimizer)):
    try:
        return await optimizer.find_nearby_stations(
            payload.location, payload.fuel_type, payload.limit_type, payload.limit_value
        )
    except RoutingNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        logging.getLogger(__name__).error("External service failure: %s", type(exc).__name__)
        raise HTTPException(
            status_code=503,
            detail="No se han podido consultar las gasolineras cercanas. Inténtalo de nuevo.",
        ) from exc
