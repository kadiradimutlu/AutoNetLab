import asyncio
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, WebSocket, WebSocketDisconnect

from app.schemas.auth import AuthenticatedUser
from app.schemas.enums import SessionStatus
from app.services.auth_service import get_user_by_token
from app.services.session_service import get_lab_session


@dataclass
class WebCliContext:
    session_id: str
    device_id: str
    container_name: str
    username: str
    role: str


class WebCliError(Exception):
    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        websocket_code: int = 1008,
    ) -> None:
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.websocket_code = websocket_code
        super().__init__(message)

    def to_payload(self) -> dict[str, Any]:
        return {
            "type": "error",
            "success": False,
            "status_code": self.status_code,
            "error_code": self.error_code,
            "message": self.message,
        }


def build_web_cli_context(
    session_id: str,
    device_id: str,
    token: str | None,
) -> WebCliContext:
    """
    Builds a validated Web CLI context / doğrulanmış Web CLI bağlamı.

    Security rules:
    - Do not accept raw container names from the browser.
    - Resolve container_name from trusted session metadata.
    - Student users may access only their own sessions.
    - Instructor users may access any session for demo/instruction purposes.
    - Lab must be deployed before opening a runtime CLI.
    """

    current_user = _authenticate_web_cli_user(token)
    session = _get_session_or_web_cli_error(session_id)

    cli_item = _find_cli_item(
        session=session,
        device_id=device_id,
    )

    _authorize_web_cli_access(
        session=session,
        current_user=current_user,
    )

    status_value = _enum_value(session.get("status"))

    if status_value != SessionStatus.deployed.value:
        raise WebCliError(
            status_code=409,
            error_code="LAB_NOT_DEPLOYED_FOR_WEB_CLI",
            message=(
                "The lab must be deployed before opening Web CLI. "
                "Deploy the lab first, then try again."
            ),
            websocket_code=1008,
        )

    container_name = _get_cli_value(cli_item, "container_name")

    if not container_name:
        raise WebCliError(
            status_code=500,
            error_code="WEB_CLI_CONTAINER_METADATA_MISSING",
            message="CLI metadata does not include a container name for this device.",
            websocket_code=1011,
        )

    return WebCliContext(
        session_id=session_id,
        device_id=device_id,
        container_name=container_name,
        username=current_user.username,
        role=current_user.role,
    )


async def run_web_cli_bridge(
    websocket: WebSocket,
    context: WebCliContext,
) -> None:
    """
    Bridges WebSocket input/output to a Docker exec shell.

    Sprint 11 MVP:
    - Uses docker exec -i <container> sh.
    - Keeps local docker exec fallback unchanged.
    - Full PTY/TTY hardening is planned for Sprint 12.
    """

    command = [
        "docker",
        "exec",
        "-i",
        context.container_name,
        "sh",
    ]

    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        await websocket.send_json(
            {
                "type": "error",
                "success": False,
                "error_code": "DOCKER_NOT_FOUND_FOR_WEB_CLI",
                "message": (
                    "Docker command was not found in the backend runtime environment. "
                    "Run the backend inside WSL/Ubuntu or the VM where Docker is installed."
                ),
            }
        )
        await _safe_close(websocket, code=1011)
        return
    except PermissionError as exc:
        await websocket.send_json(
            {
                "type": "error",
                "success": False,
                "error_code": "DOCKER_PERMISSION_DENIED_FOR_WEB_CLI",
                "message": f"Permission denied while opening Web CLI: {exc}",
            }
        )
        await _safe_close(websocket, code=1011)
        return
    except OSError as exc:
        await websocket.send_json(
            {
                "type": "error",
                "success": False,
                "error_code": "WEB_CLI_PROCESS_START_FAILED",
                "message": f"Could not start Web CLI process: {exc}",
            }
        )
        await _safe_close(websocket, code=1011)
        return

    await websocket.send_json(
        {
            "type": "runtime_started",
            "success": True,
            "session_id": context.session_id,
            "device_id": context.device_id,
            "container_name": context.container_name,
            "message": "Web CLI runtime started. Type commands and press Enter.",
        }
    )

    stdout_task = asyncio.create_task(
        _pipe_stream_to_websocket(
            stream=process.stdout,
            websocket=websocket,
            stream_name="stdout",
        )
    )
    stderr_task = asyncio.create_task(
        _pipe_stream_to_websocket(
            stream=process.stderr,
            websocket=websocket,
            stream_name="stderr",
        )
    )
    input_task = asyncio.create_task(
        _pipe_websocket_to_process(
            websocket=websocket,
            process=process,
        )
    )

    tasks = {
        stdout_task,
        stderr_task,
        input_task,
    }

    try:
        done, pending = await asyncio.wait(
            tasks,
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()

        for task in done:
            task.result()
    except WebSocketDisconnect:
        pass
    finally:
        if process.returncode is None:
            process.terminate()

            try:
                await asyncio.wait_for(process.wait(), timeout=5)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()

        await _safe_close(websocket)


async def _pipe_stream_to_websocket(
    stream: asyncio.StreamReader | None,
    websocket: WebSocket,
    stream_name: str,
) -> None:
    if stream is None:
        return

    while True:
        data = await stream.read(1024)

        if not data:
            break

        await websocket.send_text(data.decode(errors="replace"))


async def _pipe_websocket_to_process(
    websocket: WebSocket,
    process: asyncio.subprocess.Process,
) -> None:
    if process.stdin is None:
        return

    while True:
        text = await websocket.receive_text()

        process.stdin.write(text.encode())
        await process.stdin.drain()


def _authenticate_web_cli_user(token: str | None) -> AuthenticatedUser:
    if not token:
        raise WebCliError(
            status_code=401,
            error_code="WEB_CLI_AUTH_REQUIRED",
            message="Web CLI requires an authentication token.",
            websocket_code=1008,
        )

    try:
        user_payload = get_user_by_token(token)
    except HTTPException as exc:
        raise WebCliError(
            status_code=exc.status_code,
            error_code="WEB_CLI_INVALID_TOKEN",
            message=str(exc.detail),
            websocket_code=1008,
        ) from exc

    return AuthenticatedUser(**user_payload)


def _get_session_or_web_cli_error(session_id: str) -> dict:
    try:
        return get_lab_session(session_id)
    except HTTPException as exc:
        raise WebCliError(
            status_code=exc.status_code,
            error_code="WEB_CLI_SESSION_NOT_FOUND",
            message=str(exc.detail),
            websocket_code=1008,
        ) from exc


def _find_cli_item(session: dict, device_id: str) -> Any:
    for cli_item in session.get("cli_access", []):
        if _get_cli_value(cli_item, "device_id") == device_id:
            return cli_item

    raise WebCliError(
        status_code=404,
        error_code="WEB_CLI_DEVICE_NOT_FOUND",
        message=f"Device '{device_id}' is not part of this lab session.",
        websocket_code=1008,
    )


def _authorize_web_cli_access(
    session: dict,
    current_user: AuthenticatedUser,
) -> None:
    if current_user.role == "instructor":
        return

    allowed_student_ids = {
        current_user.username,
    }

    if current_user.student_id:
        allowed_student_ids.add(current_user.student_id)

    session_student_id = str(session.get("student_id", ""))

    if session_student_id not in allowed_student_ids:
        raise WebCliError(
            status_code=403,
            error_code="WEB_CLI_FORBIDDEN",
            message="Student users may only access their own lab sessions.",
            websocket_code=1008,
        )


def _get_cli_value(cli_item: Any, key: str) -> Any:
    if hasattr(cli_item, key):
        return getattr(cli_item, key)

    if isinstance(cli_item, dict):
        return cli_item.get(key)

    return None


def _enum_value(value: Any) -> str:
    if hasattr(value, "value"):
        return value.value

    return str(value)


async def _safe_close(websocket: WebSocket, code: int = 1000) -> None:
    try:
        await websocket.close(code=code)
    except RuntimeError:
        pass



def get_web_cli_readiness(
    session_id: str,
    current_user: AuthenticatedUser,
    device_id: str | None = None,
) -> dict[str, Any]:
    session = _get_session_or_web_cli_error(session_id)

    _authorize_web_cli_access(
        session=session,
        current_user=current_user,
    )

    cli_items = session.get("cli_access", [])

    if device_id is not None:
        cli_items = [
            cli_item
            for cli_item in cli_items
            if _get_cli_value(cli_item, "device_id") == device_id
        ]

        if not cli_items:
            raise HTTPException(
                status_code=404,
                detail=f"Device '{device_id}' is not part of this lab session.",
            )

    lab_status = _enum_value(session.get("status"))
    lab_deployed = lab_status == SessionStatus.deployed.value

    devices = [
        _build_device_readiness(
            cli_item=cli_item,
            lab_deployed=lab_deployed,
        )
        for cli_item in cli_items
    ]

    ready = bool(devices) and all(device["ready"] for device in devices)

    error_code = None

    if not lab_deployed:
        error_code = "LAB_NOT_DEPLOYED_FOR_WEB_CLI"
    elif not ready:
        error_code = _first_device_error_code(devices)

    return {
        "success": True,
        "session_id": session_id,
        "current_mode": "browser_cli_mvp",
        "lab_status": lab_status,
        "lab_deployed": lab_deployed,
        "ready": ready,
        "devices": devices,
        "error_code": error_code,
        "message": _readiness_message(
            lab_deployed=lab_deployed,
            ready=ready,
            device_count=len(devices),
        ),
    }


def _build_device_readiness(
    cli_item: Any,
    lab_deployed: bool,
) -> dict[str, Any]:
    device_id = _get_cli_value(cli_item, "device_id") or "unknown"
    container_name = _get_cli_value(cli_item, "container_name")

    if not lab_deployed:
        return {
            "device_id": device_id,
            "container_name": container_name,
            "docker_available": False,
            "container_running": False,
            "ready": False,
            "error_code": "LAB_NOT_DEPLOYED_FOR_WEB_CLI",
            "message": "Deploy the lab before opening Web CLI.",
        }

    if not container_name:
        return {
            "device_id": device_id,
            "container_name": None,
            "docker_available": False,
            "container_running": False,
            "ready": False,
            "error_code": "WEB_CLI_CONTAINER_METADATA_MISSING",
            "message": "Container metadata is missing for this device.",
        }

    if shutil.which("docker") is None:
        return {
            "device_id": device_id,
            "container_name": container_name,
            "docker_available": False,
            "container_running": False,
            "ready": False,
            "error_code": "DOCKER_NOT_FOUND_FOR_WEB_CLI",
            "message": "Docker command is not available in the backend runtime environment.",
        }

    try:
        completed = subprocess.run(
            [
                "docker",
                "inspect",
                "-f",
                "{{.State.Running}}",
                container_name,
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except PermissionError as exc:
        return {
            "device_id": device_id,
            "container_name": container_name,
            "docker_available": True,
            "container_running": False,
            "ready": False,
            "error_code": "DOCKER_PERMISSION_DENIED_FOR_WEB_CLI",
            "message": f"Permission denied while checking Docker container: {exc}",
        }
    except subprocess.TimeoutExpired:
        return {
            "device_id": device_id,
            "container_name": container_name,
            "docker_available": True,
            "container_running": False,
            "ready": False,
            "error_code": "WEB_CLI_CONTAINER_CHECK_TIMEOUT",
            "message": "Docker container readiness check timed out.",
        }
    except OSError as exc:
        return {
            "device_id": device_id,
            "container_name": container_name,
            "docker_available": True,
            "container_running": False,
            "ready": False,
            "error_code": "WEB_CLI_CONTAINER_CHECK_FAILED",
            "message": f"Docker container readiness check failed: {exc}",
        }

    container_running = completed.returncode == 0 and completed.stdout.strip().lower() == "true"

    if not container_running:
        return {
            "device_id": device_id,
            "container_name": container_name,
            "docker_available": True,
            "container_running": False,
            "ready": False,
            "error_code": "WEB_CLI_CONTAINER_NOT_RUNNING",
            "message": (
                "The expected lab container is not running. "
                "Deploy the lab or check Containerlab/Docker runtime state."
            ),
        }

    return {
        "device_id": device_id,
        "container_name": container_name,
        "docker_available": True,
        "container_running": True,
        "ready": True,
        "error_code": None,
        "message": "Device container is ready for Web CLI.",
    }


def _first_device_error_code(devices: list[dict[str, Any]]) -> str | None:
    for device in devices:
        if device.get("error_code"):
            return device["error_code"]

    return None


def _readiness_message(
    lab_deployed: bool,
    ready: bool,
    device_count: int,
) -> str:
    if not lab_deployed:
        return "Lab is not deployed yet. Deploy the lab before opening Web CLI."

    if device_count == 0:
        return "No CLI devices were found for this lab session."

    if ready:
        return "Web CLI runtime is ready."

    return "Web CLI runtime is not ready. Check device readiness details."
