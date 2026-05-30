import subprocess
from typing import Any

from app.schemas.enums import SessionStatus
from app.services.scenario_catalog import (
    CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID,
    SR_BASIC_LINK_SCENARIO_ID,
)


SRLINUX_CLIENT_EXPECTED_GATEWAY = "10.10.10.1"
SRLINUX_CLIENT_INJECTED_GATEWAY = "10.10.10.254"
SRLINUX_WRONG_CLIENT_GATEWAY_CODE = "SRLINUX_WRONG_CLIENT_GATEWAY"
SRLINUX_WRONG_CLIENT_GATEWAY_VARIANT_ID = "srl_basic_link_client_wrong_default_gateway"


CAMPUS_CLIENTS: dict[str, dict[str, str]] = {
    "client1": {
        "interface": "eth1",
        "ip_address": "10.10.10.10/24",
        "default_gateway": "10.10.10.1",
        "remote_peer": "10.10.20.10",
    },
    "client2": {
        "interface": "eth1",
        "ip_address": "10.10.20.10/24",
        "default_gateway": "10.10.20.1",
        "remote_peer": "10.10.10.10",
    },
}

CAMPUS_SRL_INTERFACES: dict[str, list[dict[str, str]]] = {
    "srl1": [
        {"interface": "ethernet-1/1", "ip_address": "10.10.10.1/24"},
        {"interface": "ethernet-1/2", "ip_address": "10.10.13.1/30"},
        {"interface": "ethernet-1/3", "ip_address": "10.10.14.1/30"},
    ],
    "srl2": [
        {"interface": "ethernet-1/1", "ip_address": "10.10.20.1/24"},
        {"interface": "ethernet-1/2", "ip_address": "10.10.23.1/30"},
        {"interface": "ethernet-1/3", "ip_address": "10.10.24.1/30"},
    ],
    "srl3": [
        {"interface": "ethernet-1/1", "ip_address": "10.10.13.2/30"},
        {"interface": "ethernet-1/2", "ip_address": "10.10.23.2/30"},
    ],
    "srl4": [
        {"interface": "ethernet-1/1", "ip_address": "10.10.14.2/30"},
        {"interface": "ethernet-1/2", "ip_address": "10.10.24.2/30"},
    ],
}

CAMPUS_STATIC_ROUTES: dict[str, list[dict[str, Any]]] = {
    "srl1": [
        {
            "prefix": "10.10.20.0/24",
            "next_hop": "10.10.13.2",
            "next_hop_id": 1,
            "group": "campus-srl1-to-client2",
        },
    ],
    "srl2": [
        {
            "prefix": "10.10.10.0/24",
            "next_hop": "10.10.23.2",
            "next_hop_id": 1,
            "group": "campus-srl2-to-client1",
        },
    ],
    "srl3": [
        {
            "prefix": "10.10.10.0/24",
            "next_hop": "10.10.13.1",
            "next_hop_id": 1,
            "group": "campus-srl3-to-client1",
        },
        {
            "prefix": "10.10.20.0/24",
            "next_hop": "10.10.23.1",
            "next_hop_id": 2,
            "group": "campus-srl3-to-client2",
        },
    ],
    "srl4": [
        {
            "prefix": "10.10.10.0/24",
            "next_hop": "10.10.14.1",
            "next_hop_id": 1,
            "group": "campus-srl4-to-client1",
        },
        {
            "prefix": "10.10.20.0/24",
            "next_hop": "10.10.24.1",
            "next_hop_id": 2,
            "group": "campus-srl4-to-client2",
        },
    ],
}


def build_srlinux_runtime_faults(
    *,
    difficulty: Any,
    seed: str,
) -> list[dict[str, Any]]:
    '''
    Builds deterministic SR Linux runtime faults for Sprint 30E.

    The first SR Linux scenario intentionally starts broken by making client1
    use a wrong default gateway. Student-facing API responses keep this hidden;
    validation reads live device state.
    '''

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
    '''
    Applies runtime setup for supported SR Linux scenarios.

    Basic link keeps its existing Sprint 30 behavior and can still inject the
    wrong-gateway fault after baseline setup. Campus core static routing applies
    only a golden baseline: client IP/default routes, SR Linux interface and
    network-instance bindings, and static routes. Campus runtime fault injection
    remains intentionally out of scope for NR-Sprint33A.
    '''

    session_id = str(session["session_id"])
    scenario_id = _scenario_id(session)

    if scenario_id == SR_BASIC_LINK_SCENARIO_ID:
        return _apply_basic_link_runtime_setup(
            session=session,
            session_id=session_id,
        )

    if scenario_id == CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID:
        return _apply_campus_core_static_routing_runtime_setup(
            session=session,
            session_id=session_id,
        )

    return _success_response(
        session_id=session_id,
        command_results=[],
        message="No SR Linux runtime setup was required for this scenario.",
    )


def _apply_basic_link_runtime_setup(
    *,
    session: dict[str, Any],
    session_id: str,
) -> dict[str, Any]:
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

    verification_failure = _run_basic_link_verification(
        session_id=session_id,
        command_results=command_results,
        client_container=client_container,
        srl_container=srl_container,
    )

    if verification_failure is not None:
        return verification_failure

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


def _run_basic_link_verification(
    *,
    session_id: str,
    command_results: list[dict[str, Any]],
    client_container: str,
    srl_container: str,
) -> dict[str, Any] | None:
    ping_retry_command = _ping_retry_command("10.10.10.1")

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

    return _run_verification_commands(
        session_id=session_id,
        command_results=command_results,
        verification_commands=verification_commands,
    )


def _apply_campus_core_static_routing_runtime_setup(
    *,
    session: dict[str, Any],
    session_id: str,
) -> dict[str, Any]:
    command_results: list[dict[str, Any]] = []

    required_devices = [
        *CAMPUS_CLIENTS.keys(),
        *CAMPUS_SRL_INTERFACES.keys(),
    ]
    containers = {
        device: _container_name_for_device(session, device)
        for device in required_devices
    }
    missing_devices = [
        device
        for device, container_name in containers.items()
        if not container_name
    ]

    if missing_devices:
        return _error_response(
            session_id=session_id,
            command_results=[],
            error_code="SRLINUX_CAMPUS_RUNTIME_METADATA_MISSING",
            detail=(
                "Could not resolve required campus container names for: "
                + ", ".join(sorted(missing_devices))
                + "."
            ),
        )

    for device, interfaces in CAMPUS_SRL_INTERFACES.items():
        srl_config_script = _build_campus_srl_config_script(
            device=device,
            interfaces=interfaces,
            static_routes=CAMPUS_STATIC_ROUTES.get(device, []),
        )
        result = _run_docker_exec(
            container_name=str(containers[device]),
            command=["sr_cli"],
            stage="srlinux_campus_golden_setup",
            device=device,
            display_command=f"apply campus golden SR Linux config on {device}",
            input_text=srl_config_script,
        )
        command_results.append(result)

        if not result["success"]:
            return _error_response(
                session_id=session_id,
                command_results=command_results,
                error_code="SRLINUX_CAMPUS_GOLDEN_SRL_CONFIG_FAILED",
                detail=f"Could not apply campus golden SR Linux config on {device}.",
            )

    for device, config in CAMPUS_CLIENTS.items():
        client_setup_commands = _client_setup_commands(
            interface=config["interface"],
            ip_address=config["ip_address"],
            default_gateway=config["default_gateway"],
        )

        for command in client_setup_commands:
            result = _run_docker_exec(
                container_name=str(containers[device]),
                command=["sh", "-lc", command],
                stage="campus_client_runtime_setup",
                device=device,
                display_command=command,
            )
            command_results.append(result)

            if not result["success"]:
                return _error_response(
                    session_id=session_id,
                    command_results=command_results,
                    error_code="SRLINUX_CAMPUS_CLIENT_RUNTIME_SETUP_FAILED",
                    detail=f"Campus client runtime setup command failed on {device}: {command}",
                )

    verification_failure = _run_campus_golden_verification(
        session_id=session_id,
        command_results=command_results,
        containers={device: str(name) for device, name in containers.items()},
    )

    if verification_failure is not None:
        return verification_failure

    return _success_response(
        session_id=session_id,
        command_results=command_results,
        message="SR Linux campus golden runtime setup applied successfully.",
    )


def _build_campus_srl_config_script(
    *,
    device: str,
    interfaces: list[dict[str, str]],
    static_routes: list[dict[str, Any]],
) -> str:
    lines = ["enter candidate"]

    for item in interfaces:
        interface = item["interface"]
        ip_address = item["ip_address"]
        subinterface = _subinterface_name(interface)

        lines.extend(
            [
                f"set interface {interface} admin-state enable",
                f"set interface {interface} subinterface 0 admin-state enable",
                f"set interface {interface} subinterface 0 ipv4 admin-state enable",
                f"set interface {interface} subinterface 0 ipv4 address {ip_address}",
                f"set network-instance default interface {subinterface}",
            ]
        )

    for route in static_routes:
        prefix = route["prefix"]
        next_hop = route["next_hop"]
        next_hop_id = route["next_hop_id"]
        group = route["group"]

        lines.extend(
            [
                f"set network-instance default static next-hop {next_hop_id} ip-address {next_hop}",
                f"set network-instance default static next-hop-group {group} next-hop {next_hop_id}",
                f"set network-instance default static-routes route {prefix} admin-state enable",
                f"set network-instance default static-routes route {prefix} metric 1",
                f"set network-instance default static-routes route {prefix} preference 5",
                f"set network-instance default static-routes route {prefix} static-next-hop-group {group}",
            ]
        )

    lines.extend(["commit now", "quit", ""])

    return "\n".join(lines)


def _client_setup_commands(
    *,
    interface: str,
    ip_address: str,
    default_gateway: str,
) -> list[str]:
    return [
        f"ip addr flush dev {interface} || true",
        f"ip addr add {ip_address} dev {interface}",
        f"ip link set {interface} up",
        f"ip route replace default via {default_gateway} dev {interface}",
    ]


def _run_campus_golden_verification(
    *,
    session_id: str,
    command_results: list[dict[str, Any]],
    containers: dict[str, str],
) -> dict[str, Any] | None:
    verification_commands: list[tuple[str, str, list[str], str, str]] = []

    for device, config in CAMPUS_CLIENTS.items():
        interface = config["interface"]
        verification_commands.extend(
            [
                (
                    device,
                    containers[device],
                    ["sh", "-lc", f"ip -4 addr show dev {interface}"],
                    f"verify {device} {interface} IPv4 address",
                    config["ip_address"],
                ),
                (
                    device,
                    containers[device],
                    ["sh", "-lc", "ip route"],
                    f"verify {device} default route",
                    f"default via {config['default_gateway']}",
                ),
            ]
        )

    for device, interfaces in CAMPUS_SRL_INTERFACES.items():
        for item in interfaces:
            interface = item["interface"]
            ip_address = item["ip_address"]
            verification_commands.extend(
                [
                    (
                        device,
                        containers[device],
                        [
                            "sr_cli",
                            "-ec",
                            f"info from state interface {interface} subinterface 0 ipv4",
                        ],
                        f"verify {device} {interface}.0 IPv4 address",
                        ip_address,
                    ),
                    (
                        device,
                        containers[device],
                        ["sr_cli", "-ec", "info network-instance default"],
                        f"verify {device} default network-instance binding for {interface}.0",
                        f"interface {_subinterface_name(interface)}",
                    ),
                ]
            )

    for device, routes in CAMPUS_STATIC_ROUTES.items():
        for route in routes:
            prefix = route["prefix"]
            verification_commands.append(
                (
                    device,
                    containers[device],
                    ["sr_cli", "-ec", f"info network-instance default static-routes route {prefix}"],
                    f"verify {device} static route {prefix}",
                    f"static-next-hop-group {route['group']}",
                )
            )

    verification_commands.extend(
        [
            (
                "client1",
                containers["client1"],
                ["sh", "-lc", _ping_retry_command(CAMPUS_CLIENTS["client1"]["remote_peer"])],
                "verify client1 can ping client2",
                f"bytes from {CAMPUS_CLIENTS['client1']['remote_peer']}",
            ),
            (
                "client2",
                containers["client2"],
                ["sh", "-lc", _ping_retry_command(CAMPUS_CLIENTS["client2"]["remote_peer"])],
                "verify client2 can ping client1",
                f"bytes from {CAMPUS_CLIENTS['client2']['remote_peer']}",
            ),
        ]
    )

    return _run_verification_commands(
        session_id=session_id,
        command_results=command_results,
        verification_commands=verification_commands,
    )


def _run_verification_commands(
    *,
    session_id: str,
    command_results: list[dict[str, Any]],
    verification_commands: list[tuple[str, str, list[str], str, str]],
) -> dict[str, Any] | None:
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

    return None


def _subinterface_name(interface: str) -> str:
    return f"{interface}.0"


def _ping_retry_command(ip_address: str) -> str:
    return (
        "for i in 1 2 3 4 5; do "
        f"ping -c 3 -W 2 {ip_address} && exit 0; "
        "sleep 2; "
        "done; "
        f"ping -c 3 -W 2 {ip_address}"
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
            timeout=60,
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
