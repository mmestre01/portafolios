from fastapi import Request

from app.services.optimizer import StationOptimizer
from app.services.routing import RoutingService


async def get_routing(request: Request) -> RoutingService:
    return request.app.state.routing


async def get_optimizer(request: Request) -> StationOptimizer:
    return request.app.state.optimizer
