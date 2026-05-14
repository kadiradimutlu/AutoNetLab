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
                "description": (
                    "Five injected errors with advanced scenario diversity: "
                    "addressing, subnetting, interface status, default gateway, "
                    "static routing, VLAN-like, ACL-like, and connectivity topics."
                ),
            },
        ]
    }


@router.get("/cli-access-modes")
def get_cli_access_modes() -> dict:
    return {
        "success": True,
        "current_mode": "local_docker_exec_demo",
        "default_mode": "local_docker_exec_demo",
        "modes": [
            {
                "value": "local_docker_exec_demo",
                "label": "Local docker exec demo mode",
                "status": "active",
                "description": (
                    "Stable Sprint 8 CLI access mode. Students use docker exec commands "
                    "to access Containerlab nodes in the local demo environment."
                ),
            },
            {
                "value": "ssh_gateway_planned",
                "label": "SSH Gateway",
                "status": "planned",
                "description": (
                    "Planned future mode. Requires secure user/session isolation, "
                    "credential handling, and gateway hardening."
                ),
            },
            {
                "value": "browser_cli_future_work",
                "label": "Browser-based CLI",
                "status": "future_work",
                "description": (
                    "Future work. Requires terminal streaming, WebSocket/session control, "
                    "authorization, and stronger runtime isolation."
                ),
            },
        ],
        "decision": (
            "Sprint 8 keeps docker exec local demo mode as the default and stable CLI access model. "
            "SSH Gateway and Browser-based CLI are documented but not enabled in the default flow."
        ),
        "message": "CLI access mode metadata retrieved successfully.",
    }