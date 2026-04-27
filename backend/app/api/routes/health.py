from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
def health_check() -> dict:
    return {
        "status": "ok",
        "service": "AutoNetLab Backend API",
    }