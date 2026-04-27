from fastapi import APIRouter

from app.api.routes import health, labs, meta

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(meta.router)
api_router.include_router(labs.router)