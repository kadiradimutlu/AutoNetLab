from fastapi import APIRouter

from app.schemas.enums import Difficulty

router = APIRouter(prefix="/meta", tags=["Metadata"])


@router.get("/difficulties")
def get_difficulties() -> dict:
    return {
        "difficulties": [
            {
                "value": Difficulty.easy,
                "label": "Easy",
                "description": "Two injected errors. Suitable for beginners.",
            },
            {
                "value": Difficulty.medium,
                "label": "Medium",
                "description": "Three injected errors. Suitable for intermediate users.",
            },
            {
                "value": Difficulty.hard,
                "label": "Hard",
                "description": "Five injected errors. Suitable for advanced users.",
            },
        ]
    }