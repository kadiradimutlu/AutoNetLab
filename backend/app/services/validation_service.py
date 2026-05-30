import json
import re
import subprocess
from pathlib import Path
from typing import Any

from app.schemas.enums import SessionStatus
from app.schemas.validation import ValidationCheck, ValidationResult
from app.services.validation_rules import get_live_validation_rule
from app.services.scenario_catalog import (
    CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID,
    SR_BASIC_LINK_SCENARIO_ID,
)


TOPIC_LABELS = {
    "ip_addressing": "IP Addressing",
    "subnetting": "Subnetting",
    "interface_status": "Interface Status",
    "default_gateway": "Default Gateway",
    "static_routing": "Static Routing",
    "vlan_like": "VLAN-like Configuration",
    "acl_like": "ACL-like Policy",
    "connectivity": "Connectivity",
    "routing": "Routing",
    "unknown": "Unknown",
}


TOPIC_HINTS = {
    "ip_addressing": "Check IP address and subnet mask configuration on the related interface.",
    "subnetting": "Verify subnet masks, network ranges, and whether both endpoints are in compatible subnets.",
    "interface_status": "Check whether the required interface is enabled and operational.",
    "default_gateway": "Verify that the default gateway points to the correct next-hop address.",
    "static_routing": "Review static route destination networks and next-hop addresses.",
    "vlan_like": "Check whether VLAN-like interface settings are consistent on both sides.",
    "acl_like": "Review policy-like rules that may block expected traffic.",
    "connectivity": "Use layer-by-layer troubleshooting: interface, addressing, routing, and then connectivity.",
    "routing": "Review route entries and next-hop reachability.",
    "unknown": "Review the failed validation check and troubleshoot step by step.",
}


TOPIC_BY_ERROR_CODE = {
    "IP_ADDRESS_MISMATCH": "ip_addressing",
    "WRONG_SUBNET_MASK_R1": "subnetting",
    "WRONG_SUBNET_MASK": "subnetting",
    "INTERFACE_DOWN_R2": "interface_status",
    "INTERFACE_DOWN_R4": "interface_status",
    "WRONG_GATEWAY": "default_gateway",
    "WRONG_GATEWAY_R4": "default_gateway",
    "MISSING_ROUTE": "static_routing",
    "MISSING_ROUTE_R3": "static_routing",
    "VLAN_MISMATCH": "vlan_like",
    "VLAN_MISMATCH_R3": "vlan_like",
    "ACL_BLOCK_ICMP": "acl_like",
    "ACL_BLOCK_ICMP_R1": "acl_like",
    "ACL_BLOCK_ICMP_R3": "acl_like",
    "CONNECTIVITY_FAILURE": "connectivity",
    "CONNECTIVITY_FAILURE_R2_R3": "connectivity",
    "CONNECTIVITY_FAILURE_R1_R4": "connectivity",
}


POINTS_BY_SEVERITY = {
    "low": 10,
    "medium": 20,
    "high": 25,
}


SRLINUX_PING_RETRY_COMMAND = (
    "for i in 1 2 3 4 5; do "
    "ping -c 3 -W 2 10.10.10.1 && exit 0; "
    "sleep 2; "
    "done; "
    "ping -c 3 -W 2 10.10.10.1"
)


SRLINUX_BASIC_LINK_CHECKS: list[dict[str, Any]] = [
    {
        "check_id": "srl_check_1_router_gateway_address",
        "topic": "ip_addressing",
        "device": "srl1",
        "description": "Validate that srl1 ethernet-1/1.0 has the expected gateway address.",
        "command": ["sr_cli", "-ec", "info from state interface ethernet-1/1 subinterface 0 ipv4"],
        "expected_outputs": ["10.10.10.1/24"],
        "max_points": 20,
        "hint": "Check the SR Linux interface IPv4 address and subnet mask.",
    },
    {
        "check_id": "srl_check_2_router_network_instance",
        "topic": "routing",
        "device": "srl1",
        "description": "Validate that srl1 ethernet-1/1.0 is attached to the default network-instance.",
        "command": ["sr_cli", "-ec", "info network-instance default"],
        "expected_outputs": ["interface ethernet-1/1.0"],
        "max_points": 20,
        "hint": "Check whether the SR Linux subinterface is bound to the default network-instance.",
    },
    {
        "check_id": "srl_check_3_client_address",
        "topic": "ip_addressing",
        "device": "client1",
        "description": "Validate that client1 eth1 has the expected IPv4 address.",
        "command": ["sh", "-lc", "ip -4 addr show dev eth1"],
        "expected_outputs": ["10.10.10.10/24"],
        "max_points": 20,
        "hint": "Check the client interface IPv4 address and subnet mask.",
    },
    {
        "check_id": "srl_check_4_client_default_gateway",
        "topic": "default_gateway",
        "device": "client1",
        "description": "Validate that client1 uses srl1 as its default gateway.",
        "command": ["sh", "-lc", "ip route"],
        "expected_outputs": ["default via 10.10.10.1"],
        "max_points": 20,
        "hint": "Check whether the client default route points to 10.10.10.1.",
    },
    {
        "check_id": "srl_check_5_gateway_connectivity",
        "topic": "connectivity",
        "device": "client1",
        "description": "Validate that client1 can ping the SR Linux gateway.",
        "command": ["sh", "-lc", SRLINUX_PING_RETRY_COMMAND],
        "expected_outputs": ["bytes from 10.10.10.1"],
        "max_points": 20,
        "hint": "Check addressing, network-instance binding, default gateway, and ARP settling.",
    },
]


def _campus_ping_retry_command(ip_address: str) -> str:
    return (
        "for i in 1 2 3 4 5; do "
        f"ping -c 3 -W 2 {ip_address} && exit 0; "
        "sleep 2; "
        "done; "
        f"ping -c 3 -W 2 {ip_address}"
    )


CAMPUS_CORE_STATIC_ROUTING_CHECKS: list[dict[str, Any]] = [
    {
        "check_id": "campus_check_1_client1_address",
        "topic": "ip_addressing",
        "device": "client1",
        "description": "Validate that client1 eth1 has the expected campus IPv4 address.",
        "command": ["sh", "-lc", "ip -4 addr show dev eth1"],
        "expected_outputs": ["10.10.10.10/24"],
        "max_points": 10,
        "hint": "Check client1 eth1 addressing against the campus addressing table.",
    },
    {
        "check_id": "campus_check_2_client1_default_gateway",
        "topic": "default_gateway",
        "device": "client1",
        "description": "Validate that client1 uses srl1 as its default gateway.",
        "command": ["sh", "-lc", "ip route"],
        "expected_outputs": ["default via 10.10.10.1"],
        "max_points": 10,
        "hint": "Check whether client1 default route points to 10.10.10.1.",
    },
    {
        "check_id": "campus_check_3_client2_address",
        "topic": "ip_addressing",
        "device": "client2",
        "description": "Validate that client2 eth1 has the expected campus IPv4 address.",
        "command": ["sh", "-lc", "ip -4 addr show dev eth1"],
        "expected_outputs": ["10.10.20.10/24"],
        "max_points": 10,
        "hint": "Check client2 eth1 addressing against the campus addressing table.",
    },
    {
        "check_id": "campus_check_4_client2_default_gateway",
        "topic": "default_gateway",
        "device": "client2",
        "description": "Validate that client2 uses srl2 as its default gateway.",
        "command": ["sh", "-lc", "ip route"],
        "expected_outputs": ["default via 10.10.20.1"],
        "max_points": 10,
        "hint": "Check whether client2 default route points to 10.10.20.1.",
    },
    {
        "check_id": "campus_check_5_client1_to_client2_connectivity",
        "topic": "connectivity",
        "device": "client1",
        "description": "Validate that client1 can reach client2 across the campus core.",
        "command": ["sh", "-lc", _campus_ping_retry_command("10.10.20.10")],
        "expected_outputs": ["bytes from 10.10.20.10"],
        "max_points": 10,
        "hint": "Check client addressing, default gateways, SR Linux routes, and core reachability.",
    },
    {
        "check_id": "campus_check_6_client2_to_client1_connectivity",
        "topic": "connectivity",
        "device": "client2",
        "description": "Validate that client2 can reach client1 across the campus core.",
        "command": ["sh", "-lc", _campus_ping_retry_command("10.10.10.10")],
        "expected_outputs": ["bytes from 10.10.10.10"],
        "max_points": 10,
        "hint": "Check return-path routing from the campus core toward client1.",
    },
    {
        "check_id": "campus_check_7_srl1_edge_and_core_interfaces",
        "topic": "ip_addressing",
        "device": "srl1",
        "description": "Validate that srl1 has the expected client-edge interface address.",
        "command": ["sr_cli", "-ec", "info from state interface ethernet-1/1 subinterface 0 ipv4"],
        "expected_outputs": ["10.10.10.1/24"],
        "max_points": 10,
        "hint": "Check srl1 ethernet-1/1 subinterface IPv4 addressing.",
    },
    {
        "check_id": "campus_check_8_srl2_edge_and_core_interfaces",
        "topic": "ip_addressing",
        "device": "srl2",
        "description": "Validate that srl2 has the expected client-edge interface address.",
        "command": ["sr_cli", "-ec", "info from state interface ethernet-1/1 subinterface 0 ipv4"],
        "expected_outputs": ["10.10.20.1/24"],
        "max_points": 10,
        "hint": "Check srl2 ethernet-1/1 subinterface IPv4 addressing.",
    },
    {
        "check_id": "campus_check_9_srl3_transit_routes",
        "topic": "static_routing",
        "device": "srl3",
        "description": "Validate that srl3 has primary transit routes for both campus client networks.",
        "command": ["sr_cli", "-ec", "info network-instance default static-routes"],
        "expected_outputs": ["campus-srl3-to-client1", "campus-srl3-to-client2"],
        "max_points": 10,
        "hint": "Check srl3 static routes and next-hop groups toward both client networks.",
    },
    {
        "check_id": "campus_check_10_srl1_route_to_client2",
        "topic": "static_routing",
        "device": "srl1",
        "description": "Validate that srl1 has a static route toward the client2 network.",
        "command": ["sr_cli", "-ec", "info network-instance default static-routes route 10.10.20.0/24"],
        "expected_outputs": ["campus-srl1-to-client2"],
        "max_points": 10,
        "hint": "Check srl1 route to 10.10.20.0/24 through the campus core.",
    },
    {
        "check_id": "campus_check_11_srl2_route_to_client1",
        "topic": "static_routing",
        "device": "srl2",
        "description": "Validate that srl2 has a static route toward the client1 network.",
        "command": ["sr_cli", "-ec", "info network-instance default static-routes route 10.10.10.0/24"],
        "expected_outputs": ["campus-srl2-to-client1"],
        "max_points": 10,
        "hint": "Check srl2 route to 10.10.10.0/24 through the campus core.",
    },
]


def validate_session(session: dict) -> ValidationResult:
    """
    Validation Service v2 / Doğrulama Servisi v2.

    Sprint 8 goals:
    - Keep the existing marker-based validation stable.
    - Add richer validation checks / daha detaylı doğrulama kontrolleri.
    - Use topic taxonomy / konu sınıflandırması for recommendation and analytics.
    - Prepare evidence / observed state fields without exposing full solution data.
    """

    if _is_campus_core_static_routing_session(session):
        return _validate_campus_core_static_routing_session(session)

    if _is_srlinux_basic_link_session(session):
        return _validate_srlinux_basic_link_session(session)

    session_dir = _get_session_dir(session)
    injected_errors = _load_injected_errors(
        session=session,
        session_dir=session_dir,
    )

    checks: list[ValidationCheck] = []

    for index, error in enumerate(injected_errors, start=1):
        check = _build_validation_check(
            index=index,
            error=error,
            session=session,
            session_dir=session_dir,
        )
        checks.append(check)

    earned_points = sum(check.points for check in checks)
    max_points = sum(check.max_points for check in checks)

    score = int((earned_points / max_points) * 100) if max_points else 100
    overall_passed = score == 100

    recommendations = _build_recommendations(checks)

    return ValidationResult(
        session_id=session["session_id"],
        status=SessionStatus.validated,
        passed=overall_passed,
        score=score,
        checks=checks,
        recommendations=recommendations,
    )



def _scenario_id_for_session(session: dict) -> str | None:
    scenario = session.get("scenario")

    if isinstance(scenario, dict):
        scenario_id = scenario.get("id")
        if scenario_id:
            return str(scenario_id)

    topology_template = session.get("topology_template")
    if topology_template:
        return str(topology_template)

    return None


def _is_srlinux_basic_link_session(session: dict) -> bool:
    return _scenario_id_for_session(session) == SR_BASIC_LINK_SCENARIO_ID


def _is_campus_core_static_routing_session(session: dict) -> bool:
    return _scenario_id_for_session(session) == CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID


def _validate_campus_core_static_routing_session(session: dict) -> ValidationResult:
    if not _runtime_status_allows_live_validation(session):
        return _build_live_validation_unavailable_result(
            session=session,
            scenario_label="Campus core static routing",
        )

    checks = [
        _build_srlinux_validation_check(
            index=index,
            spec=spec,
            session=session,
        )
        for index, spec in enumerate(CAMPUS_CORE_STATIC_ROUTING_CHECKS, start=1)
    ]

    earned_points = sum(check.points for check in checks)
    max_points = sum(check.max_points for check in checks)

    score = int((earned_points / max_points) * 100) if max_points else 100
    overall_passed = score == 100
    recommendations = _build_recommendations(checks)

    return ValidationResult(
        session_id=session["session_id"],
        status=SessionStatus.validated,
        passed=overall_passed,
        score=score,
        checks=checks,
        recommendations=recommendations,
    )


def _runtime_status_allows_live_validation(session: dict) -> bool:
    status_value = session.get("status")

    if hasattr(status_value, "value"):
        status_value = status_value.value

    return str(status_value or "").lower() in {"deployed", "validated"}


def _build_live_validation_unavailable_result(
    *,
    session: dict,
    scenario_label: str,
) -> ValidationResult:
    check = ValidationCheck(
        check_id="campus_check_runtime_deployed",
        topic="connectivity",
        description=f"Validate that {scenario_label} runtime is deployed before live validation.",
        status="failed",
        passed=False,
        points=0,
        max_points=100,
        message=(
            f"{scenario_label} live validation could not run because the lab "
            "runtime is not deployed."
        ),
        hint="Deploy the lab first, then run validation again.",
        evidence={
            "validation_mode": "srlinux_live_state_precheck",
            "observed_state": "runtime status is not deployed or validated",
            "status": str(session.get("status")),
        },
    )

    return ValidationResult(
        session_id=session["session_id"],
        status=SessionStatus.validated,
        passed=False,
        score=0,
        checks=[check],
        recommendations=["Deploy the lab runtime before running live validation."],
    )


def _validate_srlinux_basic_link_session(session: dict) -> ValidationResult:
    checks = [
        _build_srlinux_validation_check(
            index=index,
            spec=spec,
            session=session,
        )
        for index, spec in enumerate(SRLINUX_BASIC_LINK_CHECKS, start=1)
    ]

    earned_points = sum(check.points for check in checks)
    max_points = sum(check.max_points for check in checks)

    score = int((earned_points / max_points) * 100) if max_points else 100
    overall_passed = score == 100
    recommendations = _build_recommendations(checks)

    return ValidationResult(
        session_id=session["session_id"],
        status=SessionStatus.validated,
        passed=overall_passed,
        score=score,
        checks=checks,
        recommendations=recommendations,
    )


def _build_srlinux_validation_check(
    *,
    index: int,
    spec: dict[str, Any],
    session: dict,
) -> ValidationCheck:
    device = str(spec["device"])
    topic = str(spec["topic"])
    topic_label = _topic_label(topic)
    expected_outputs = [
        str(expected)
        for expected in spec.get("expected_outputs", [])
        if str(expected).strip()
    ]
    max_points = int(spec.get("max_points", 20))

    container_name = _container_name_for_device(
        session=session,
        device=device,
    )

    if not container_name:
        return ValidationCheck(
            check_id=str(spec.get("check_id") or f"srl_check_{index}_{topic}"),
            topic=topic,
            description=str(spec.get("description") or _build_check_description(topic=topic, device=device)),
            status="failed",
            passed=False,
            points=0,
            max_points=max_points,
            message=f"{topic_label} validation failed on {device}: runtime container metadata was not found.",
            hint=str(spec.get("hint") or TOPIC_HINTS.get(topic, TOPIC_HINTS["unknown"])),
            evidence={
                "validation_mode": "srlinux_live_state_check",
                "device": device,
                "container_name": None,
                "command": _command_display(spec["command"]),
                "expected_state": _expected_state_payload(expected_outputs),
                "missing_expected_outputs": expected_outputs,
                "observed_state": "runtime container metadata missing",
                "observed_output": "",
            },
        )

    observed = _run_device_command(
        container_name=container_name,
        command=spec["command"],
        timeout=int(spec.get("timeout", 20)),
    )

    missing_outputs = [
        expected
        for expected in expected_outputs
        if expected not in observed["output"]
    ]

    passed = observed["return_code"] == 0 and not missing_outputs
    points = max_points if passed else 0
    status = "passed" if passed else "failed"

    if passed:
        message = f"{topic_label} validation passed on {device}."
        observed_state = "expected SR Linux scenario live state is present"
    else:
        message = f"{topic_label} validation failed on {device}. Expected SR Linux scenario state is missing."
        observed_state = "expected SR Linux scenario live state is missing"

    return ValidationCheck(
        check_id=str(spec.get("check_id") or f"srl_check_{index}_{topic}"),
        topic=topic,
        description=str(spec.get("description") or _build_check_description(topic=topic, device=device)),
        status=status,
        passed=passed,
        points=points,
        max_points=max_points,
        message=message,
        hint=str(spec.get("hint") or TOPIC_HINTS.get(topic, TOPIC_HINTS["unknown"])),
        evidence={
            "validation_mode": "srlinux_live_state_check",
            "device": device,
            "container_name": container_name,
            "command": _command_display(spec["command"]),
            "expected_state": _expected_state_payload(expected_outputs),
            "missing_expected_outputs": missing_outputs,
            "observed_state": observed_state,
            "return_code": observed["return_code"],
            "observed_output": observed["output"][:2000],
        },
    )


def _run_device_command(
    *,
    container_name: str,
    command: list[str],
    timeout: int,
) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            ["docker", "exec", container_name, *command],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        return {
            "return_code": None,
            "stdout": "",
            "stderr": str(exc),
            "output": str(exc),
        }
    except PermissionError as exc:
        return {
            "return_code": None,
            "stdout": "",
            "stderr": str(exc),
            "output": str(exc),
        }
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or "Command timed out."
        output = "\n".join(value for value in [stdout, stderr] if value)
        return {
            "return_code": None,
            "stdout": stdout,
            "stderr": stderr,
            "output": output,
        }

    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    output = "\n".join(value.strip() for value in [stdout, stderr] if value.strip())

    return {
        "return_code": completed.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "output": output,
    }


def _command_display(command: list[str]) -> str:
    return " ".join(str(part) for part in command)


def _expected_state_payload(expected_outputs: list[str]) -> str | list[str]:
    if len(expected_outputs) == 1:
        return expected_outputs[0]

    return list(expected_outputs)


def _build_validation_check(
    index: int,
    error: dict[str, Any],
    session: dict,
    session_dir: Path,
) -> ValidationCheck:
    code = str(error.get("code", "UNKNOWN_ERROR"))
    raw_topic = error.get("topic", "unknown")
    topic = _topic_from_error_code_or_label(code=code, raw_topic=raw_topic)

    device = str(error.get("device", "unknown"))
    severity = str(error.get("severity", "medium")).lower()
    max_points = POINTS_BY_SEVERITY.get(severity, POINTS_BY_SEVERITY["medium"])

    config_path = session_dir / "configs" / f"{device}.conf"

    evaluation = _evaluate_error_fix(
        config_path=config_path,
        code=code,
        topic=topic,
        device=device,
        session=session,
        error=error,
    )

    passed = evaluation["passed"]
    points = max_points if passed else 0
    status = "passed" if passed else "failed"

    return ValidationCheck(
        check_id=f"check_{index}_{topic}",
        topic=topic,
        description=_build_check_description(topic=topic, device=device),
        status=status,
        passed=passed,
        points=points,
        max_points=max_points,
        message=evaluation["message"],
        hint=TOPIC_HINTS.get(topic, TOPIC_HINTS["unknown"]),
        evidence=evaluation["evidence"],
    )


def _get_session_dir(session: dict) -> Path:
    topology_file = session.get("topology_file")

    if topology_file:
        return Path(topology_file).parent

    return Path("containerlab") / "generated" / session["session_id"]


def _load_injected_errors(
    session: dict,
    session_dir: Path,
) -> list[dict[str, Any]]:
    metadata_path = session_dir / "errors" / "injected_errors.json"

    if metadata_path.exists():
        with metadata_path.open("r", encoding="utf-8") as file:
            payload = json.load(file)

        errors = payload.get("injected_errors", [])

        if isinstance(errors, list):
            return errors

    fallback_errors = session.get("injected_errors", [])

    normalized_errors: list[dict[str, Any]] = []

    for error in fallback_errors:
        if hasattr(error, "model_dump"):
            normalized_errors.append(error.model_dump())
        elif isinstance(error, dict):
            normalized_errors.append(error)

    return normalized_errors


def _evaluate_error_fix(
    config_path: Path,
    code: str,
    topic: str,
    device: str,
    session: dict,
    error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    topic_label = _topic_label(topic)

    live_evaluation = _evaluate_live_container_state(
        session=session,
        code=code,
        topic=topic,
        device=device,
        error=error,
    )
    if live_evaluation is not None:
        return live_evaluation

    if not config_path.exists():
        return {
            "passed": False,
            "message": f"{topic_label} validation failed on {device}: config file was not found.",
            "evidence": {
                "validation_mode": "config_marker_check",
                "device": device,
                "config_file": config_path.name,
                "config_file_present": False,
                "observed_state": "config file missing",
            },
        }

    content = config_path.read_text(encoding="utf-8")
    marker_present = code in content

    if marker_present:
        return {
            "passed": False,
            "message": f"{topic_label} validation failed on {device}. The related issue still appears unresolved.",
            "evidence": {
                "validation_mode": "config_marker_check",
                "device": device,
                "config_file": config_path.name,
                "config_file_present": True,
                "observed_state": "issue marker is still present",
            },
        }

    return {
        "passed": True,
        "message": f"{topic_label} validation passed on {device}.",
        "evidence": {
            "validation_mode": "config_marker_check",
            "device": device,
            "config_file": config_path.name,
            "config_file_present": True,
            "observed_state": "issue marker is no longer present",
        },
    }


def _evaluate_live_container_state(
    session: dict,
    code: str,
    topic: str,
    device: str,
    error: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    status_value = session.get("status")
    if hasattr(status_value, "value"):
        status_value = status_value.value

    if status_value is not None and str(status_value).lower() not in {"deployed", "validated"}:
        return None

    session_rule = _session_validation_rule_from_error(error)

    if session_rule is not None:
        command = session_rule["command"]
        expected_outputs = session_rule["expected_outputs"]
        rule_description = session_rule["description"]
    else:
        rule = get_live_validation_rule(code)

        if rule is None:
            return None

        command = rule.command
        expected_outputs = list(rule.expected_outputs)
        rule_description = rule.description

    container_name = _container_name_for_device(session=session, device=device)
    if not container_name:
        return None

    observed = _run_container_command(
        container_name=container_name,
        command=command,
    )
    if observed is None:
        return None

    missing_outputs = [
        expected
        for expected in expected_outputs
        if expected not in observed
    ]

    passed = not missing_outputs
    topic_label = _topic_label(topic)

    if passed:
        message = f"{topic_label} validation passed on {device}."
        observed_state = "expected live state is present"
    else:
        message = f"{topic_label} validation failed on {device}. The related issue still appears unresolved."
        observed_state = "expected live state is missing"

    expected_state: str | list[str]
    if len(expected_outputs) == 1:
        expected_state = expected_outputs[0]
    else:
        expected_state = list(expected_outputs)

    return {
        "passed": passed,
        "message": message,
        "evidence": {
            "validation_mode": "live_container_state_check",
            "device": device,
            "container_name": container_name,
            "command": command,
            "rule_description": rule_description,
            "expected_state": expected_state,
            "missing_expected_outputs": missing_outputs,
            "observed_state": observed_state,
            "observed_output": observed[:2000],
        },
    }


def _session_validation_rule_from_error(error: dict[str, Any] | None) -> dict[str, Any] | None:
    if not error:
        return None

    command = error.get("validation_command")
    expected_outputs = error.get("expected_outputs", [])

    if isinstance(expected_outputs, str):
        expected_outputs = [expected_outputs]

    normalized_outputs = [
        str(expected)
        for expected in expected_outputs
        if str(expected).strip()
    ]

    if not command or not normalized_outputs:
        return None

    return {
        "command": str(command),
        "expected_outputs": normalized_outputs,
        "description": str(
            error.get("description")
            or error.get("variant_id")
            or error.get("code")
            or "Session-specific validation rule"
        ),
    }


def _entry_value(entry: Any, key: str) -> Any:
    if isinstance(entry, dict):
        return entry.get(key)
    return getattr(entry, key, None)


def _container_name_for_device(session: dict, device: str) -> str | None:
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


def _run_container_command(container_name: str, command: str) -> str | None:
    try:
        completed = subprocess.run(
            ["docker", "exec", container_name, "sh", "-lc", command],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None

    output = completed.stdout.strip() or completed.stderr.strip()

    if completed.returncode != 0:
        normalized_output = output.lower()

        if (
            "no such container" in normalized_output
            or "is not running" in normalized_output
            or "container not found" in normalized_output
            or "error during connect" in normalized_output
            or "cannot connect to the docker daemon" in normalized_output
            or "is the docker daemon running" in normalized_output
            or "docker daemon" in normalized_output
        ):
            return None

        return output

    return output


def _build_recommendations(checks: list[ValidationCheck]) -> list[str]:
    failed_topics = []

    for check in checks:
        if not check.passed and check.topic not in failed_topics:
            failed_topics.append(check.topic)

    if not failed_topics:
        return ["All validation checks passed. Good job."]

    return [
        f"Review and fix topic: {_topic_label(topic)}"
        for topic in failed_topics
    ]


def _topic_from_error_code_or_label(code: str, raw_topic: Any) -> str:
    if code in TOPIC_BY_ERROR_CODE:
        return TOPIC_BY_ERROR_CODE[code]

    return _normalize_topic(raw_topic)


def _normalize_topic(value: Any) -> str:
    if value is None:
        return "unknown"

    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = text.strip("_")

    if text == "ip_addressing":
        return "ip_addressing"

    if text in {"vlan", "vlan_mismatch"}:
        return "vlan_like"

    if text in {"acl", "access_control"}:
        return "acl_like"

    if text in {"routing", "static_route", "static_routes"}:
        return "static_routing"

    return text or "unknown"


def _topic_label(topic: str) -> str:
    return TOPIC_LABELS.get(topic, topic.replace("_", " ").title())


def _build_check_description(topic: str, device: str) -> str:
    topic_label = _topic_label(topic)

    return f"Validate whether {topic_label} related configuration state is correct on {device}."