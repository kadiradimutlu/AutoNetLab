import subprocess
from typing import Any

from app.schemas.enums import SessionStatus


BASELINE_COMMANDS_BY_DEVICE = {
    "r1": [
        "ip route del 10.10.12.2/32 || true",
        "ip route del 10.10.23.1/32 || true",
        "if ip link show eth1 >/dev/null 2>&1; then ip addr flush dev eth1; ip addr add 10.10.12.1/24 dev eth1; ip link set eth1 up; fi",
        "if ip link show eth2 >/dev/null 2>&1; then ip addr flush dev eth2; ip addr add 10.10.14.1/24 dev eth2; ip link set eth2 up; fi",
        "ip route replace 10.10.23.0/24 via 10.10.12.2 || true",
        "if ip link show eth2 >/dev/null 2>&1; then ip route replace 10.10.34.0/24 via 10.10.14.2 || true; fi",
    ],
    "r2": [
        "ip route del 10.10.23.2/32 || true",
        "if ip link show eth1 >/dev/null 2>&1; then ip addr flush dev eth1; ip addr add 10.10.12.2/24 dev eth1; ip link set eth1 up; fi",
        "if ip link show eth2 >/dev/null 2>&1; then ip addr flush dev eth2; ip addr add 10.10.23.1/24 dev eth2; ip link set eth2 up; fi",
        "ip route replace default via 10.10.12.1 || true",
        "ip route replace 10.10.14.0/24 via 10.10.12.1 || true",
        "if ip link show eth2 >/dev/null 2>&1; then ip route replace 10.10.34.0/24 via 10.10.23.2 || true; fi",
    ],
    "r3": [
        "ip route del 10.10.23.1/32 || true",
        "if ip link show eth1 >/dev/null 2>&1; then ip addr flush dev eth1; ip addr add 10.10.23.2/24 dev eth1; ip link set eth1 up; fi",
        "if ip link show eth2 >/dev/null 2>&1; then ip addr flush dev eth2; ip addr add 10.10.34.1/24 dev eth2; ip link set eth2 up; fi",
        "if ip link show eth1 >/dev/null 2>&1; then ip route replace 10.10.12.0/24 via 10.10.23.1 || true; fi",
        "if ip link show eth2 >/dev/null 2>&1; then ip route replace 10.10.14.0/24 via 10.10.34.2 || true; fi",
    ],
    "r4": [
        "ip route del 10.10.14.1/32 || true",
        "if ip link show eth1 >/dev/null 2>&1; then ip addr flush dev eth1; ip addr add 10.10.34.2/24 dev eth1; ip link set eth1 up; fi",
        "if ip link show eth2 >/dev/null 2>&1; then ip addr flush dev eth2; ip addr add 10.10.14.2/24 dev eth2; ip link set eth2 up; fi",
        "if ip link show eth1 >/dev/null 2>&1; then ip route replace default via 10.10.34.1 || true; fi",
        "if ip link show eth1 >/dev/null 2>&1; then ip route replace 10.10.23.0/24 via 10.10.34.1 || true; fi",
        "if ip link show eth2 >/dev/null 2>&1; then ip route replace 10.10.12.0/24 via 10.10.14.1 || true; fi",
    ],
}


def apply_runtime_error_injection(session: dict[str, Any]) -> dict[str, Any]:
    """
    Applies the real runtime lab state after Containerlab deployment.

    Flow:
    1. Normalize every device into the golden baseline.
    2. Apply only the randomly selected injected error commands.
    3. Store validation metadata in the session from the create step.

    This makes the deployed lab realistically broken instead of only writing
    config-marker files.
    """

    session_id = str(session["session_id"])
    command_results: list[dict[str, Any]] = []

    baseline_result = _apply_golden_baseline(
        session=session,
        command_results=command_results,
    )
    if baseline_result is not None:
        return baseline_result

    for error in _normalized_errors(session.get("injected_errors", [])):
        device = str(error.get("device", ""))
        injection_commands = [
            str(command)
            for command in error.get("injection_commands", [])
            if str(command).strip()
        ]

        if not device or not injection_commands:
            continue

        container_name = _container_name_for_device(session=session, device=device)
        if not container_name:
            return _runtime_error_response(
                session_id=session_id,
                command_results=command_results,
                error_code="RUNTIME_INJECTION_CONTAINER_NOT_FOUND",
                detail=f"Container metadata for device '{device}' was not found.",
            )

        for command in injection_commands:
            result = _run_container_command(
                container_name=container_name,
                command=command,
            )
            command_results.append(
                {
                    "stage": "inject_error",
                    "device": device,
                    "code": error.get("code"),
                    "variant_id": error.get("variant_id"),
                    "container_name": container_name,
                    "command": command,
                    "return_code": result["return_code"],
                    "stdout": result["stdout"],
                    "stderr": result["stderr"],
                }
            )

            if result["return_code"] != 0:
                return _runtime_error_response(
                    session_id=session_id,
                    command_results=command_results,
                    error_code="RUNTIME_ERROR_INJECTION_COMMAND_FAILED",
                    detail=(
                        f"Runtime injection command failed for {device} "
                        f"({error.get('code')})."
                    ),
                )

    return {
        "success": True,
        "session_id": session_id,
        "status": SessionStatus.deployed,
        "message": "Runtime error injection applied successfully.",
        "command": "docker exec runtime baseline and injected error commands",
        "return_code": 0,
        "stdout": _format_command_results(command_results, stream="stdout"),
        "stderr": _format_command_results(command_results, stream="stderr"),
        "error_code": None,
        "detail": None,
        "suggestion": None,
    }


def _apply_golden_baseline(
    session: dict[str, Any],
    command_results: list[dict[str, Any]],
) -> dict[str, Any] | None:
    session_id = str(session["session_id"])

    for cli_entry in session.get("cli_access", []):
        device = str(_entry_value(cli_entry, "device_id") or _entry_value(cli_entry, "name") or "")
        container_name = str(_entry_value(cli_entry, "container_name") or "")

        if not device or not container_name:
            continue

        baseline_commands = BASELINE_COMMANDS_BY_DEVICE.get(device, [])

        for command in baseline_commands:
            result = _run_container_command(
                container_name=container_name,
                command=command,
            )
            command_results.append(
                {
                    "stage": "golden_baseline",
                    "device": device,
                    "code": None,
                    "variant_id": None,
                    "container_name": container_name,
                    "command": command,
                    "return_code": result["return_code"],
                    "stdout": result["stdout"],
                    "stderr": result["stderr"],
                }
            )

            if result["return_code"] != 0:
                return _runtime_error_response(
                    session_id=session_id,
                    command_results=command_results,
                    error_code="RUNTIME_BASELINE_COMMAND_FAILED",
                    detail=f"Golden baseline command failed for {device}.",
                )

    return None


def _run_container_command(container_name: str, command: str) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            ["docker", "exec", container_name, "sh", "-lc", command],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except FileNotFoundError:
        return {
            "return_code": 127,
            "stdout": "",
            "stderr": "docker command was not found",
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "return_code": 124,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "runtime command timed out",
        }

    return {
        "return_code": completed.returncode,
        "stdout": completed.stdout or "",
        "stderr": completed.stderr or "",
    }


def _runtime_error_response(
    session_id: str,
    command_results: list[dict[str, Any]],
    error_code: str,
    detail: str,
) -> dict[str, Any]:
    return {
        "success": False,
        "session_id": session_id,
        "status": SessionStatus.error,
        "message": "Containerlab deployed, but runtime error injection failed.",
        "command": "docker exec runtime baseline and injected error commands",
        "return_code": 1,
        "stdout": _format_command_results(command_results, stream="stdout"),
        "stderr": _format_command_results(command_results, stream="stderr"),
        "error_code": error_code,
        "detail": detail,
        "suggestion": (
            "Inspect Docker containers and retry deployment. "
            "If the problem persists, destroy the lab and create a new session."
        ),
    }


def _format_command_results(command_results: list[dict[str, Any]], stream: str) -> str:
    lines: list[str] = []

    for item in command_results:
        value = str(item.get(stream) or "").strip()

        if not value:
            continue

        lines.append(
            "[{stage}] {device} {command}\n{value}".format(
                stage=item.get("stage"),
                device=item.get("device"),
                command=item.get("command"),
                value=value,
            )
        )

    return "\n\n".join(lines)


def _container_name_for_device(session: dict[str, Any], device: str) -> str | None:
    for entry in session.get("cli_access", []):
        entry_device_id = _entry_value(entry, "device_id")
        entry_name = _entry_value(entry, "name")

        if entry_device_id == device or entry_name == device:
            container_name = _entry_value(entry, "container_name")
            if container_name:
                return str(container_name)

    lab_name = session.get("lab_name")
    if lab_name:
        return f"clab-{lab_name}-{device}"

    session_id = session.get("session_id")
    if session_id:
        return f"clab-autonetlab-{session_id}-{device}"

    return None


def _normalized_errors(errors: Any) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []

    for error in errors or []:
        if hasattr(error, "model_dump"):
            normalized.append(error.model_dump())
        elif isinstance(error, dict):
            normalized.append(error)

    return normalized


def _entry_value(entry: Any, key: str) -> Any:
    if isinstance(entry, dict):
        return entry.get(key)

    return getattr(entry, key, None)
