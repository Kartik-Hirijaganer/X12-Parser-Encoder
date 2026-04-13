"""API router registration."""

from fastapi import APIRouter

from app.core.config import settings
from app.routers.convert import router as convert_router
from app.routers.export import router as export_router
from app.routers.generate import router as generate_router
from app.routers.health import router as health_router
from app.routers.parse import router as parse_router
from app.routers.pipeline import router as pipeline_router
from app.routers.profiles import router as profiles_router
from app.routers.templates import router as templates_router
from app.routers.validate import router as validate_router

api_router = APIRouter(prefix=settings.api_v1_prefix)
api_router.include_router(convert_router)
api_router.include_router(generate_router)
api_router.include_router(validate_router)
api_router.include_router(parse_router)
api_router.include_router(export_router)
api_router.include_router(pipeline_router)
api_router.include_router(profiles_router)
api_router.include_router(templates_router)
api_router.include_router(health_router)

__all__ = ["api_router"]
