from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings


def get_cors_origins() -> list[str]:
    """
    Returns allowed CORS origins for local frontend development.

    settings.cors_origins keeps config-based origins.
    local_frontend_origins covers Vite dev server ports used during Sprint 1/2.
    """
    configured_origins = settings.cors_origins or []

    local_frontend_origins = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ]

    return list(dict.fromkeys(configured_origins + local_frontend_origins))


app = FastAPI(
    title=settings.app_name,
    description="Backend API / Orchestrator for AutoNetLab.",
    version="0.1.0",
)

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
        "message": "Welcome to AutoNetLab Backend API",
        "docs": "/docs",
        "health": f"{settings.api_prefix}/health",
    }