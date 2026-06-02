import asyncio
import json
import os
import select
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, WebSocket, WebSocketDisconnect

from app.schemas.auth import AuthenticatedUser
from app.schemas.enums import SessionStatus
from app.services.auth_service import get_user_by_token
from app.services.session_service import get_lab_session, is_runtime_active_status


@dataclass
class WebCliContext:
    session_id: str
    device_id: str
    container_name: str
    username: str
    role: str
    terminal_command: list[str]


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

    if not is_runtime_active_status(status_value):
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
        terminal_command=_build_terminal_command(
            cli_item=cli_item,
            container_name=container_name,
        ),
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

        await _cancel_pending_tasks(pending)

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



async def run_terminal_pty_bridge(
    websocket: WebSocket,
    context: WebCliContext,
) -> None:
    """
    Bridges a WebSocket to a real Docker exec TTY via a backend PTY.

    NR-Sprint36A:
    - Uses docker exec -it <container> <trusted command>.
    - Allocates a backend PTY so interactive terminal behavior works.
    - Forwards raw bytes in both directions.
    - Preserves CTRL+C and escape sequences for arrows/function keys.
    - Supports resize control frames: {"type":"resize","cols":120,"rows":32}.
    """

    command = [
        "docker",
        "exec",
        "-it",
        context.container_name,
        *context.terminal_command,
    ]

    try:
        master_fd, slave_fd = _open_terminal_pty()
    except TerminalPtyUnavailableError as exc:
        await websocket.send_json(
            {
                "type": "error",
                "success": False,
                "error_code": "TERMINAL_PTY_UNAVAILABLE",
                "message": str(exc),
            }
        )
        await _safe_close(websocket, code=1011)
        return
    except OSError as exc:
        await websocket.send_json(
            {
                "type": "error",
                "success": False,
                "error_code": "TERMINAL_PTY_START_FAILED",
                "message": f"Could not allocate backend PTY: {exc}",
            }
        )
        await _safe_close(websocket, code=1011)
        return

    process: asyncio.subprocess.Process | None = None

    try:
        os.set_blocking(master_fd, False)

        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                close_fds=True,
            )
        finally:
            _close_fd(slave_fd)

        await websocket.send_json(
            {
                "type": "terminal_started",
                "success": True,
                "session_id": context.session_id,
                "device_id": context.device_id,
                "container_name": context.container_name,
                "mode": "terminal_pty_bridge",
                "terminal_command": context.terminal_command,
                "protocol": {
                    "input": "binary frames or text frames are forwarded as raw terminal bytes",
                    "output": "terminal output is sent as binary frames",
                    "resize": {"type": "resize", "cols": 120, "rows": 32},
                },
                "message": "Real terminal PTY bridge started.",
            }
        )

        output_task = asyncio.create_task(
            _pipe_terminal_pty_to_websocket(
                master_fd=master_fd,
                websocket=websocket,
            )
        )
        input_task = asyncio.create_task(
            _pipe_websocket_to_terminal_pty(
                websocket=websocket,
                master_fd=master_fd,
            )
        )

        process_wait_task = asyncio.create_task(process.wait())

        done, pending = await asyncio.wait(
            {output_task, input_task, process_wait_task},
            return_when=asyncio.FIRST_COMPLETED,
        )

        await _cancel_pending_tasks(pending)

        for task in done:
            task.result()
    except FileNotFoundError:
        await websocket.send_json(
            {
                "type": "error",
                "success": False,
                "error_code": "DOCKER_NOT_FOUND_FOR_TERMINAL",
                "message": (
                    "Docker command was not found in the backend runtime environment. "
                    "Run the backend inside WSL/Ubuntu or the VM where Docker is installed."
                ),
            }
        )
    except PermissionError as exc:
        await websocket.send_json(
            {
                "type": "error",
                "success": False,
                "error_code": "DOCKER_PERMISSION_DENIED_FOR_TERMINAL",
                "message": f"Permission denied while opening terminal: {exc}",
            }
        )
    except WebSocketDisconnect:
        pass
    except OSError as exc:
        await websocket.send_json(
            {
                "type": "error",
                "success": False,
                "error_code": "TERMINAL_PTY_BRIDGE_FAILED",
                "message": f"Terminal PTY bridge failed: {exc}",
            }
        )
    finally:
        if process is not None and process.returncode is None:
            process.terminate()

            try:
                await asyncio.wait_for(process.wait(), timeout=5)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()

        _close_fd(master_fd)
        await _safe_close(websocket)



async def _cancel_pending_tasks(tasks: set[asyncio.Task]) -> None:
    if not tasks:
        return

    for task in tasks:
        task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)



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



class TerminalPtyUnavailableError(RuntimeError):
    pass


def _build_terminal_command(cli_item: Any, container_name: str) -> list[str]:
    command_text = _get_cli_value(cli_item, "command")

    if isinstance(command_text, str) and command_text.strip():
        try:
            tokens = shlex.split(command_text)
        except ValueError:
            tokens = []

        if container_name in tokens:
            container_index = tokens.index(container_name)
            terminal_command = tokens[container_index + 1 :]

            if terminal_command:
                return terminal_command

    return ["sh"]


def _open_terminal_pty() -> tuple[int, int]:
    try:
        import pty
    except ImportError as exc:
        raise TerminalPtyUnavailableError(
            "Backend PTY support is only available on Unix-like runtimes such as the Ubuntu VM."
        ) from exc

    return pty.openpty()


def _websocket_message_to_terminal_input(
    message: dict[str, Any],
) -> tuple[bytes | None, dict[str, int] | None]:
    raw_bytes = message.get("bytes")

    if raw_bytes is not None:
        return raw_bytes, None

    text = message.get("text")

    if text is None:
        return None, None

    control_message = _parse_terminal_control_message(text)

    if control_message is not None:
        return None, control_message

    return text.encode(), None


def _parse_terminal_control_message(text: str) -> dict[str, int] | None:
    stripped = text.strip()

    if not stripped.startswith("{"):
        return None

    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        return None

    if payload.get("type") != "resize":
        return None

    try:
        cols = int(payload["cols"])
        rows = int(payload["rows"])
    except (KeyError, TypeError, ValueError):
        return None

    if cols < 1 or rows < 1:
        return None

    return {
        "type": "resize",
        "cols": cols,
        "rows": rows,
    }


async def _pipe_terminal_pty_to_websocket(
    master_fd: int,
    websocket: WebSocket,
) -> None:
    while True:
        data = await asyncio.to_thread(_read_terminal_pty_chunk, master_fd)

        if not data:
            continue

        await websocket.send_bytes(data)


def _read_terminal_pty_chunk(master_fd: int) -> bytes:
    ready, _, _ = select.select([master_fd], [], [], 0.25)

    if not ready:
        return b""

    try:
        return os.read(master_fd, 4096)
    except BlockingIOError:
        return b""
    except OSError:
        return b""


async def _pipe_websocket_to_terminal_pty(
    websocket: WebSocket,
    master_fd: int,
) -> None:
    while True:
        message = await websocket.receive()

        if message.get("type") == "websocket.disconnect":
            raise WebSocketDisconnect

        terminal_input, control_message = _websocket_message_to_terminal_input(message)

        if control_message is not None:
            _resize_terminal_pty(
                master_fd=master_fd,
                cols=control_message["cols"],
                rows=control_message["rows"],
            )
            continue

        if terminal_input is None:
            continue

        await asyncio.to_thread(_write_terminal_pty_input, master_fd, terminal_input)


def _write_terminal_pty_input(master_fd: int, terminal_input: bytes) -> None:
    if not terminal_input:
        return

    os.write(master_fd, terminal_input)


def _resize_terminal_pty(master_fd: int, cols: int, rows: int) -> None:
    try:
        import fcntl
        import struct
        import termios
    except ImportError:
        return

    if cols < 1 or rows < 1:
        return

    fcntl.ioctl(
        master_fd,
        termios.TIOCSWINSZ,
        struct.pack("HHHH", rows, cols, 0, 0),
    )


def _close_fd(fd: int) -> None:
    try:
        os.close(fd)
    except OSError:
        pass



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
    lab_deployed = is_runtime_active_status(lab_status)

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

