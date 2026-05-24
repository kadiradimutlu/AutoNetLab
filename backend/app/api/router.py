from fastapi import APIRouter

from app.api.routes import auth, health, instructor, labs, meta

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(meta.router)
api_router.include_router(labs.router)
api_router.include_router(instructor.router)
