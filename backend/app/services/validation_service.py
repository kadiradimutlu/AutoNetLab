import json
import re
from pathlib import Path
from typing import Any

from app.schemas.enums import SessionStatus
from app.schemas.validation import ValidationCheck, ValidationResult


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
    "CONNECTIVITY_FAILURE": "connectivity",
}


POINTS_BY_SEVERITY = {
    "low": 10,
    "medium": 20,
    "high": 25,
}


def validate_session(session: dict) -> ValidationResult:
    """
    Validation Service v2 / Doğrulama Servisi v2.

    Sprint 8 goals:
    - Keep the existing marker-based validation stable.
    - Add richer validation checks / daha detaylı doğrulama kontrolleri.
    - Use topic taxonomy / konu sınıflandırması for recommendation and analytics.
    - Prepare evidence / observed state fields without exposing full solution data.
    """

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


def _build_validation_check(
    index: int,
    error: dict[str, Any],
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
) -> dict[str, Any]:
    topic_label = _topic_label(topic)

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