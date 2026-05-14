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
        "current_mode": "browser_cli_mvp",
        "default_mode": "browser_cli_mvp",
        "fallback_mode": "local_docker_exec_demo_fallback",
        "modes": [
            {
                "value": "browser_cli_mvp",
                "label": "Browser-based CLI MVP",
                "status": "active",
                "description": (
                    "Sprint 11 active CLI access mode. The frontend connects to a "
                    "backend WebSocket endpoint and the backend bridges the session "
                    "to the lab container CLI."
                ),
            },
            {
                "value": "local_docker_exec_demo",
                "label": "Local docker exec demo mode",
                "status": "supported",
                "description": (
                    "Existing CLI access mode. Students can still use docker exec "
                    "commands locally as a fallback during development or demo recovery."
                ),
            },
            {
                "value": "local_docker_exec_demo_fallback",
                "label": "Local docker exec fallback",
                "status": "fallback",
                "description": (
                    "Fallback mode kept for reliability if browser CLI is unavailable "
                    "during a local or VM demo."
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
                "label": "Browser-based CLI hardening",
                "status": "future_work",
                "description": (
                    "Future hardening work for terminal resizing, PTY support, "
                    "stronger stream lifecycle handling, and production-grade isolation."
                ),
            },
        ],
        "websocket": {
            "path_template": "/api/v1/labs/{session_id}/cli/ws/{device_id}",
            "auth_query_param": "token",
            "example": (
                "ws://127.0.0.1:8000/api/v1/labs/"
                "lab-abc12345/cli/ws/r1?token=demo-student-token"
            ),
        },
        "decision": (
            "Sprint 11 enables browser_cli_mvp as the primary CLI access mode. "
            "local_docker_exec_demo remains available as fallback."
        ),
        "message": "CLI access mode metadata retrieved successfully.",
    }
