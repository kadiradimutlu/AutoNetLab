import subprocess
from typing import Any

from app.schemas.enums import SessionStatus
from app.services.scenario_catalog import SR_BASIC_LINK_SCENARIO_ID


SRLINUX_CLIENT_EXPECTED_GATEWAY = "10.10.10.1"
SRLINUX_CLIENT_INJECTED_GATEWAY = "10.10.10.254"
SRLINUX_WRONG_CLIENT_GATEWAY_CODE = "SRLINUX_WRONG_CLIENT_GATEWAY"
SRLINUX_WRONG_CLIENT_GATEWAY_VARIANT_ID = "srl_basic_link_client_wrong_default_gateway"


def build_srlinux_runtime_faults(
    *,
    difficulty: Any,
    seed: str,
) -> list[dict[str, Any]]:
    """
    Builds deterministic SR Linux runtime faults for Sprint 30E.

    The first SR Linux scenario intentionally starts broken by making client1
    use a wrong default gateway. Student-facing API responses keep this hidden;
    validation reads live device state.
    """

    return [
        {
            "code": SRLINUX_WRONG_CLIENT_GATEWAY_CODE,
            "topic": "default_gateway",
            "device": "client1",
            "description": "client1 has an incorrect default gateway for the SR Linux link.",
            "severity": "medium",
            "variant_id": SRLINUX_WRONG_CLIENT_GATEWAY_VARIANT_ID,
            "interface": "eth1",
            "validation_command": "ip route",
            "expected_outputs": [f"default via {SRLINUX_CLIENT_EXPECTED_GATEWAY}"],
            "injection_commands": [
                f"ip route replace default via {SRLINUX_CLIENT_INJECTED_GATEWAY} dev eth1"
            ],
        }
    ]




def apply_srlinux_runtime_setup(session: dict[str, Any]) -> dict[str, Any]:
    """
    Applies runtime setup for Sprint 30 SR Linux scenarios.

    Containerlab link-level ipv4 metadata configures the SR Linux interface IP,
    but SR Linux still needs the routed subinterface to be attached to the
    default network-instance. The Linux client side also needs explicit
    IP/default-gateway setup after deploy.
    """

    session_id = str(session["session_id"])
    scenario_id = _scenario_id(session)

    if scenario_id != SR_BASIC_LINK_SCENARIO_ID:
        return _success_response(
            session_id=session_id,
            command_results=[],
            message="No SR Linux runtime setup was required for this scenario.",
        )

    client_container = _container_name_for_device(session, "client1")
    srl_container = _container_name_for_device(session, "srl1")

    if not client_container or not srl_container:
        return _error_response(
            session_id=session_id,
            command_results=[],
            error_code="SRLINUX_RUNTIME_METADATA_MISSING",
            detail="Could not resolve required container names for srl1/client1.",
        )

    command_results: list[dict[str, Any]] = []

    srl_config_script = "\n".join(
        [
            "enter candidate",
            "set network-instance default interface ethernet-1/1.0",
            "commit now",
            "quit",
            "",
        ]
    )

    srl_config_result = _run_docker_exec(
        container_name=srl_container,
        command=["sr_cli"],
        stage="srlinux_network_instance_setup",
        device="srl1",
        display_command="bind ethernet-1/1.0 to default network-instance",
        input_text=srl_config_script,
    )
    command_results.append(srl_config_result)

    if not srl_config_result["success"]:
        return _error_response(
            session_id=session_id,
            command_results=command_results,
            error_code="SRLINUX_NETWORK_INSTANCE_SETUP_FAILED",
            detail="Could not bind ethernet-1/1.0 to SR Linux default network-instance.",
        )

    client_setup_commands = [
        "ip addr flush dev eth1 || true",
        "ip addr add 10.10.10.10/24 dev eth1",
        "ip link set eth1 up",
        "ip route replace default via 10.10.10.1 dev eth1",
    ]

    for command in client_setup_commands:
        result = _run_docker_exec(
            container_name=client_container,
            command=["sh", "-lc", command],
            stage="client_runtime_setup",
            device="client1",
            display_command=command,
        )
        command_results.append(result)

        if not result["success"]:
            return _error_response(
                session_id=session_id,
                command_results=command_results,
                error_code="SRLINUX_CLIENT_RUNTIME_SETUP_FAILED",
                detail=f"Client runtime setup command failed: {command}",
            )

    ping_retry_command = (
        "for i in 1 2 3 4 5; do "
        "ping -c 3 -W 2 10.10.10.1 && exit 0; "
        "sleep 2; "
        "done; "
        "ping -c 3 -W 2 10.10.10.1"
    )

    verification_commands = [
        (
            "client1",
            client_container,
            ["sh", "-lc", "ip -4 addr show dev eth1"],
            "verify client1 eth1 IPv4 address",
            "10.10.10.10/24",
        ),
        (
            "client1",
            client_container,
            ["sh", "-lc", "ip route"],
            "verify client1 default route",
            "default via 10.10.10.1",
        ),
        (
            "srl1",
            srl_container,
            ["sr_cli", "-ec", "info from state interface ethernet-1/1 subinterface 0 ipv4"],
            "verify srl1 gateway address",
            "10.10.10.1/24",
        ),
        (
            "srl1",
            srl_container,
            ["sr_cli", "-ec", "info network-instance default"],
            "verify srl1 default network-instance binding",
            "interface ethernet-1/1.0",
        ),
        (
            "client1",
            client_container,
            ["sh", "-lc", ping_retry_command],
            "verify client1 can ping srl1 gateway",
            "bytes from 10.10.10.1",
        ),
    ]

    for device, container_name, command, display_command, expected_output in verification_commands:
        result = _run_docker_exec(
            container_name=container_name,
            command=command,
            stage="srlinux_runtime_verification",
            device=device,
            display_command=display_command,
        )
        command_results.append(result)

        if not result["success"] or expected_output not in result.get("stdout", ""):
            return _error_response(
                session_id=session_id,
                command_results=command_results,
                error_code="SRLINUX_RUNTIME_VERIFICATION_FAILED",
                detail=(
                    f"Runtime verification failed for {device}: "
                    f"expected output '{expected_output}' while running '{display_command}'."
                ),
            )

    fault_failure = _apply_srlinux_runtime_fault_injection(
        session=session,
        command_results=command_results,
    )

    if fault_failure is not None:
        return _error_response(
            session_id=session_id,
            command_results=command_results,
            error_code=fault_failure["error_code"],
            detail=fault_failure["detail"],
        )

    return _success_response(
        session_id=session_id,
        command_results=command_results,
        message="SR Linux runtime setup applied successfully.",
    )


def _run_docker_exec(
    *,
    container_name: str,
    command: list[str],
    stage: str,
    device: str,
    display_command: str,
    input_text: str | None = None,
) -> dict[str, Any]:
    docker_command = ["docker", "exec"]

    if input_text is not None:
        docker_command.append("-i")

    docker_command.extend([container_name, *command])

    try:
        completed = subprocess.run(
            docker_command,
            input=input_text,
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )
    except FileNotFoundError as exc:
        return {
            "stage": stage,
            "device": device,
            "command": display_command,
            "success": False,
            "return_code": None,
            "stdout": "",
            "stderr": str(exc),
        }
    except PermissionError as exc:
        return {
            "stage": stage,
            "device": device,
            "command": display_command,
            "success": False,
            "return_code": None,
            "stdout": "",
            "stderr": str(exc),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "stage": stage,
            "device": device,
            "command": display_command,
            "success": False,
            "return_code": None,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "Command timed out.",
        }

    return {
        "stage": stage,
        "device": device,
        "command": display_command,
        "success": completed.returncode == 0,
        "return_code": completed.returncode,
        "stdout": completed.stdout or "",
        "stderr": completed.stderr or "",
    }


def _success_response(
    *,
    session_id: str,
    command_results: list[dict[str, Any]],
    message: str,
) -> dict[str, Any]:
    return {
        "success": True,
        "session_id": session_id,
        "status": SessionStatus.deployed,
        "message": message,
        "command": "docker exec SR Linux runtime setup commands",
        "return_code": 0,
        "stdout": _format_command_results(command_results, stream="stdout"),
        "stderr": _format_command_results(command_results, stream="stderr"),
        "error_code": None,
        "detail": None,
        "suggestion": None,
    }


def _error_response(
    *,
    session_id: str,
    command_results: list[dict[str, Any]],
    error_code: str,
    detail: str,
) -> dict[str, Any]:
    return {
        "success": False,
        "session_id": session_id,
        "status": SessionStatus.error,
        "message": "Containerlab deployed, but SR Linux runtime setup failed.",
        "command": "docker exec SR Linux runtime setup commands",
        "return_code": 1,
        "stdout": _format_command_results(command_results, stream="stdout"),
        "stderr": _format_command_results(command_results, stream="stderr"),
        "error_code": error_code,
        "detail": detail,
        "suggestion": (
            "Inspect SR Linux and client containers, then retry deployment. "
            "If resources remain, destroy the lab before creating a new session."
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
    for entry in session.get("cli_access", []) or []:
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


def _scenario_id(session: dict[str, Any]) -> str | None:
    scenario = session.get("scenario")

    if isinstance(scenario, dict):
        return scenario.get("id")

    return None



def _apply_srlinux_runtime_fault_injection(
    *,
    session: dict[str, Any],
    command_results: list[dict[str, Any]],
) -> dict[str, str] | None:
    faults = _srlinux_faults_for_session(session)

    for fault in faults:
        device = str(fault.get("device") or "")
        container_name = _container_name_for_device(session, device)

        if not container_name:
            return {
                "error_code": "SRLINUX_RUNTIME_FAULT_METADATA_MISSING",
                "detail": f"Could not resolve container name for SR Linux runtime fault device: {device}.",
            }

        commands = [
            str(command)
            for command in fault.get("injection_commands", [])
            if str(command).strip()
        ]

        if not commands:
            return {
                "error_code": "SRLINUX_RUNTIME_FAULT_COMMAND_MISSING",
                "detail": f"No runtime fault injection commands were defined for {fault.get('variant_id') or fault.get('code')}.",
            }

        for command in commands:
            result = _run_docker_exec(
                container_name=container_name,
                command=["sh", "-lc", command],
                stage="srlinux_runtime_fault_injection",
                device=device,
                display_command=command,
            )
            command_results.append(result)

            if not result["success"]:
                return {
                    "error_code": "SRLINUX_RUNTIME_FAULT_INJECTION_FAILED",
                    "detail": (
                        f"SR Linux runtime fault injection failed for {device}: "
                        f"{command}"
                    ),
                }

    return None


def _srlinux_faults_for_session(session: dict[str, Any]) -> list[dict[str, Any]]:
    faults: list[dict[str, Any]] = []

    for fault in _normalized_errors(session.get("injected_errors")):
        code = str(fault.get("code") or "")
        variant_id = str(fault.get("variant_id") or "")

        if (
            code == SRLINUX_WRONG_CLIENT_GATEWAY_CODE
            or variant_id == SRLINUX_WRONG_CLIENT_GATEWAY_VARIANT_ID
        ):
            faults.append(fault)

    return faults


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
