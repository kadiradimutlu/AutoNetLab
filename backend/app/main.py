from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.error_handlers import register_exception_handlers


def get_cors_origins() -> list[str]:
    """
    Returns allowed CORS origins from application settings.

    Local development and production deployment origins are configured through
    CORS_ORIGINS in backend/.env.
    """
    return settings.get_cors_origins()


app = FastAPI(
    title=settings.app_name,
    description="Backend API / Orchestrator for AutoNetLab.",
    version="0.1.0",
)

register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/")
def root() -> dict:
    return {
        "success": True,
        "message": "Welcome to AutoNetLab Backend API",
        "docs": "/docs",
        "health": f"{settings.api_prefix}/health",
    }
