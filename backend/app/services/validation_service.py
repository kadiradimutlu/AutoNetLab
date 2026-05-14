import json
from pathlib import Path
from typing import Any

from app.schemas.enums import SessionStatus
from app.schemas.validation import ValidationCheck, ValidationResult


def validate_session(session: dict) -> ValidationResult:
    """
    Validation Service v1 / Doğrulama Servisi v1.

    Sprint 1 used mock validation.
    Sprint 2 reads session-specific injected error metadata and config files.

    MVP validation logic:
    - Read containerlab/generated/<session_id>/errors/injected_errors.json
    - For each injected error, read configs/<device>.conf
    - If the error code still exists in the config file, the issue is not fixed.
    - If the error code is removed from the config file, the issue is considered fixed.
    """

    session_dir = _get_session_dir(session)
    injected_errors = _load_injected_errors(
        session=session,
        session_dir=session_dir,
    )

    checks: list[ValidationCheck] = []

    for index, error in enumerate(injected_errors, start=1):
        code = error.get("code", "UNKNOWN_ERROR")
        topic = error.get("topic", "Unknown")
        device = error.get("device", "unknown")
        description = error.get("description", "No description provided.")

        config_path = session_dir / "configs" / f"{device}.conf"

        passed, message = _evaluate_error_fix(
            config_path=config_path,
            code=code,
            topic=topic,
            device=device,
            description=description,
        )

        checks.append(
            ValidationCheck(
                check_id=f"check_{index}_{code.lower()}",
                topic=topic,
                passed=passed,
                message=message,
            )
        )

    passed_count = sum(1 for check in checks if check.passed)
    score = int((passed_count / len(checks)) * 100) if checks else 100
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
    description: str,
) -> tuple[bool, str]:
    if not config_path.exists():
        return (
            False,
            f"{device} config file was not found. Cannot validate {topic} issue: {description}",
        )

    content = config_path.read_text(encoding="utf-8")

    if code in content:
        return (
            False,
            f"{topic} issue still exists on {device}: {description}",
        )

    return (
        True,
        f"{topic} issue appears to be fixed on {device}.",
    )


def _build_recommendations(checks: list[ValidationCheck]) -> list[str]:
    failed_topics = []

    for check in checks:
        if not check.passed and check.topic not in failed_topics:
            failed_topics.append(check.topic)

    if not failed_topics:
        return ["All injected issues appear to be fixed. Good job."]

    return [
        f"Review and fix topic: {topic}"
        for topic in failed_topics
    ]
