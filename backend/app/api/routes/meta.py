import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from app.db.session import get_database_readiness

from app.schemas.enums import Difficulty
from app.services.containerlab_adapter import GENERATED_DIR, PROJECT_ROOT, TEMPLATES_DIR
from app.services.scenario_catalog import list_scenarios

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


@router.get("/scenarios")
def get_scenarios() -> dict:
    return {
        "success": True,
        "scenarios": list_scenarios(),
        "message": "Scenario catalog retrieved successfully.",
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


@router.get("/runtime-readiness")
def get_runtime_readiness() -> dict:
    docker_available = shutil.which("docker") is not None
    containerlab_available = shutil.which("containerlab") is not None

    docker_version_result = _run_command(["docker", "--version"]) if docker_available else None
    docker_ps_result = _run_command(["docker", "ps"]) if docker_available else None
    containerlab_version_result = (
        _run_command(["containerlab", "version"]) if containerlab_available else None
    )

    docker_ps_ok = bool(docker_ps_result and docker_ps_result["success"])
    containerlab_version_ok = bool(
        containerlab_version_result and containerlab_version_result["success"]
    )

    templates_dir_exists = TEMPLATES_DIR.exists()
    generated_dir_exists = GENERATED_DIR.exists()

    checks = [
        _check_item(
            name="docker_available",
            ok=docker_available,
            message=(
                "Docker command is available."
                if docker_available
                else "Docker command is not available in the backend runtime PATH."
            ),
        ),
        _check_item(
            name="docker_ps",
            ok=docker_ps_ok,
            message=(
                "Docker daemon is reachable."
                if docker_ps_ok
                else "Docker daemon is not reachable or docker ps failed."
            ),
        ),
        _check_item(
            name="containerlab_available",
            ok=containerlab_available,
            message=(
                "Containerlab command is available."
                if containerlab_available
                else "Containerlab command is not available in the backend runtime PATH."
            ),
        ),
        _check_item(
            name="containerlab_version",
            ok=containerlab_version_ok,
            message=(
                "Containerlab version command succeeded."
                if containerlab_version_ok
                else "Containerlab version command failed or could not be executed."
            ),
        ),
        _check_item(
            name="templates_dir_exists",
            ok=templates_dir_exists,
            message=(
                "Containerlab templates directory exists."
                if templates_dir_exists
                else "Containerlab templates directory is missing."
            ),
        ),
    ]

    ready = all(item["ok"] for item in checks)

    return {
        "success": True,
        "ready": ready,
        "platform": platform.system(),
        "platform_release": platform.release(),
        "recommended_backend_environment": "WSL/Ubuntu or Linux VM with Docker and Containerlab.",
        "project_root": str(PROJECT_ROOT),
        "templates_dir": str(TEMPLATES_DIR),
        "templates_dir_exists": templates_dir_exists,
        "generated_dir": str(GENERATED_DIR),
        "generated_dir_exists": generated_dir_exists,
        "docker_available": docker_available,
        "docker_version": _stdout_or_none(docker_version_result),
        "docker_ps_ok": docker_ps_ok,
        "containerlab_available": containerlab_available,
        "containerlab_version": _stdout_or_none(containerlab_version_result),
        "current_mode": "browser_cli_mvp",
        "fallback_mode": "local_docker_exec_demo_fallback",
        "checks": checks,
        "message": (
            "Runtime environment is ready for the demo."
            if ready
            else "Runtime environment is not fully ready. Review failed checks."
        ),
    }

@router.get("/database-readiness")
def get_database_runtime_readiness() -> dict:
    return get_database_readiness()

def _run_command(command: list[str]) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except FileNotFoundError as exc:
        return {
            "success": False,
            "return_code": None,
            "stdout": "",
            "stderr": str(exc),
        }
    except PermissionError as exc:
        return {
            "success": False,
            "return_code": None,
            "stdout": "",
            "stderr": str(exc),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "success": False,
            "return_code": None,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "Command timed out.",
        }

    return {
        "success": completed.returncode == 0,
        "return_code": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def _stdout_or_none(result: dict[str, Any] | None) -> str | None:
    if not result:
        return None

    return result.get("stdout") or None


def _check_item(name: str, ok: bool, message: str) -> dict:
    return {
        "name": name,
        "ok": ok,
        "message": message,
    }
