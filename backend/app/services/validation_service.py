from app.schemas.enums import SessionStatus
from app.schemas.validation import ValidationCheck, ValidationResult


def validate_session(session: dict) -> ValidationResult:
    """
    Sprint 1 MVP validation service.

    For now, this function creates mock validation checks.
    Later, this service will run real Python validation scripts.
    """

    checks: list[ValidationCheck] = []

    for index, error in enumerate(session["injected_errors"], start=1):
        passed = index % 2 == 0

        checks.append(
            ValidationCheck(
                check_id=f"check_{index}_{error.code.lower()}",
                topic=error.topic,
                passed=passed,
                message=(
                    f"{error.topic} check passed."
                    if passed
                    else f"{error.topic} issue still exists: {error.description}"
                ),
            )
        )

    passed_count = sum(1 for check in checks if check.passed)
    score = int((passed_count / len(checks)) * 100) if checks else 100
    overall_passed = score == 100

    recommendations = []
    for check in checks:
        if not check.passed:
            recommendations.append(f"Review topic: {check.topic}")

    return ValidationResult(
        session_id=session["session_id"],
        status=SessionStatus.validated,
        passed=overall_passed,
        score=score,
        checks=checks,
        recommendations=recommendations,
    )