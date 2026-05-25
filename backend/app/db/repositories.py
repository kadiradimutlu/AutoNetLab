
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models import (
    LabSessionRecord,
    RecommendationRecord,
    User,
    ValidationAttemptRecord,
    ValidationResultRecord,
)
from app.db.session import session_scope


logger = logging.getLogger(__name__)


def persist_lab_session_snapshot(session_payload: dict[str, Any]) -> bool:
    """
    Best-effort PostgreSQL/SQL persistence for lab session metadata.

    The existing session.json filesystem persistence remains the compatibility
    fallback. Database errors are logged and must not break the runtime lab flow.
    """

    try:
        with session_scope() as db:
            _upsert_lab_session(db=db, session_payload=session_payload)
        return True
    except SQLAlchemyError:
        logger.warning("Database lab session persistence failed.", exc_info=True)
        return False
    except Exception:
        logger.warning("Unexpected lab session persistence failure.", exc_info=True)
        return False


def persist_validation_result_snapshot(
    session_payload: dict[str, Any],
    validation_result_payload: dict[str, Any],
) -> bool:
    """
    Best-effort persistence for validation outcomes.

    Keeps the database aligned with the file-backed session metadata without
    making PostgreSQL a hard runtime dependency during Sprint 16.
    """

    try:
        with session_scope() as db:
            _upsert_lab_session(db=db, session_payload=session_payload)
            session_id = str(session_payload["session_id"])
            _upsert_validation_result(
                db=db,
                session_id=session_id,
                validation_result_payload=validation_result_payload,
            )
            _upsert_validation_attempt(
                db=db,
                session_id=session_id,
                validation_result_payload=validation_result_payload,
            )
        return True
    except SQLAlchemyError:
        logger.warning("Database validation result persistence failed.", exc_info=True)
        return False
    except Exception:
        logger.warning("Unexpected validation result persistence failure.", exc_info=True)
        return False


def persist_recommendation_snapshot(
    session_payload: dict[str, Any],
    recommendation_payload: dict[str, Any],
) -> bool:
    """
    Best-effort persistence for generated recommendation payloads.

    Recommendation history is append-only for Sprint 16 so instructor analytics
    can later analyze recommendation evolution over time.
    """

    try:
        with session_scope() as db:
            _upsert_lab_session(db=db, session_payload=session_payload)

            db.add(
                RecommendationRecord(
                    session_id=str(session_payload["session_id"]),
                    source=str(recommendation_payload.get("source", "unknown")),
                    fallback_used=bool(recommendation_payload.get("fallback_used", False)),
                    recommendations_json=_json_value(
                        recommendation_payload.get("recommendations", [])
                    ),
                    raw_payload_json=_json_value(recommendation_payload),
                )
            )

        return True
    except SQLAlchemyError:
        logger.warning("Database recommendation persistence failed.", exc_info=True)
        return False
    except Exception:
        logger.warning("Unexpected recommendation persistence failure.", exc_info=True)
        return False


def _upsert_user(db: Session, username: str) -> None:
    user = db.get(User, username)

    if user is None:
        db.add(
            User(
                username=username,
                display_name=username,
                role="student",
                student_id=username,
            )
        )
        return

    user.display_name = user.display_name or username
    user.role = user.role or "student"
    user.student_id = user.student_id or username


def _upsert_lab_session(db: Session, session_payload: dict[str, Any]) -> None:
    session_id = str(session_payload["session_id"])
    student_id = str(session_payload.get("student_id") or "unknown")

    _upsert_user(db=db, username=student_id)

    record = db.get(LabSessionRecord, session_id)

    if record is None:
        record = LabSessionRecord(
            session_id=session_id,
            student_id=student_id,
            difficulty=_enum_value(session_payload.get("difficulty")),
            status=_enum_value(session_payload.get("status")),
            topology_template=str(session_payload.get("topology_template") or "unknown"),
            lab_name=str(session_payload.get("lab_name") or session_id),
            topology_file=str(session_payload.get("topology_file") or ""),
            topology_json=_json_value(session_payload.get("topology") or {}),
            cli_access_json=_json_value(session_payload.get("cli_access") or []),
            injected_errors_json=_json_value(session_payload.get("injected_errors") or []),
            topic_performance_json=_json_value(session_payload.get("topic_performance")),
            score=session_payload.get("score"),
            passed=session_payload.get("passed"),
            created_at=_parse_datetime(session_payload.get("created_at")),
            completed_at=_parse_optional_datetime(session_payload.get("completed_at")),
        )
        db.add(record)
        return

    record.student_id = student_id
    record.difficulty = _enum_value(session_payload.get("difficulty"))
    record.status = _enum_value(session_payload.get("status"))
    record.topology_template = str(session_payload.get("topology_template") or "unknown")
    record.lab_name = str(session_payload.get("lab_name") or session_id)
    record.topology_file = str(session_payload.get("topology_file") or "")
    record.topology_json = _json_value(session_payload.get("topology") or {})
    record.cli_access_json = _json_value(session_payload.get("cli_access") or [])
    record.injected_errors_json = _json_value(session_payload.get("injected_errors") or [])
    record.topic_performance_json = _json_value(session_payload.get("topic_performance"))
    record.score = session_payload.get("score")
    record.passed = session_payload.get("passed")
    record.created_at = _parse_datetime(session_payload.get("created_at"))
    record.completed_at = _parse_optional_datetime(session_payload.get("completed_at"))


def _upsert_validation_result(
    db: Session,
    session_id: str,
    validation_result_payload: dict[str, Any],
) -> None:
    record = (
        db.query(ValidationResultRecord)
        .filter(ValidationResultRecord.session_id == session_id)
        .one_or_none()
    )

    if record is None:
        record = ValidationResultRecord(
            session_id=session_id,
            status=_enum_value(validation_result_payload.get("status")),
            passed=bool(validation_result_payload.get("passed", False)),
            score=int(validation_result_payload.get("score", 0)),
            checks_json=_json_value(validation_result_payload.get("checks", [])),
            recommendations_json=_json_value(validation_result_payload.get("recommendations", [])),
            raw_result_json=_json_value(validation_result_payload),
        )
        db.add(record)
        return

    record.status = _enum_value(validation_result_payload.get("status"))
    record.passed = bool(validation_result_payload.get("passed", False))
    record.score = int(validation_result_payload.get("score", 0))
    record.checks_json = _json_value(validation_result_payload.get("checks", []))
    record.recommendations_json = _json_value(validation_result_payload.get("recommendations", []))
    record.raw_result_json = _json_value(validation_result_payload)


def _upsert_validation_attempt(
    db: Session,
    session_id: str,
    validation_result_payload: dict[str, Any],
) -> None:
    attempt_number = int(validation_result_payload.get("attempt_number") or 0)

    if attempt_number <= 0:
        latest_attempt_number = (
            db.query(func.max(ValidationAttemptRecord.attempt_number))
            .filter(ValidationAttemptRecord.session_id == session_id)
            .scalar()
            or 0
        )
        attempt_number = int(latest_attempt_number) + 1

    record = (
        db.query(ValidationAttemptRecord)
        .filter(
            ValidationAttemptRecord.session_id == session_id,
            ValidationAttemptRecord.attempt_number == attempt_number,
        )
        .one_or_none()
    )

    checks = _json_value(validation_result_payload.get("checks", []))
    recommendations = _json_value(validation_result_payload.get("recommendations", []))
    raw_result = _json_value(validation_result_payload)

    passed_checks = int(
        validation_result_payload.get("passed_checks")
        or sum(1 for check in checks if check.get("passed") is True)
    )
    failed_checks = int(
        validation_result_payload.get("failed_checks")
        or sum(1 for check in checks if check.get("passed") is False)
    )

    created_at = _parse_datetime(validation_result_payload.get("created_at"))

    if record is None:
        db.add(
            ValidationAttemptRecord(
                session_id=session_id,
                attempt_number=attempt_number,
                status=_enum_value(validation_result_payload.get("status")),
                passed=bool(validation_result_payload.get("passed", False)),
                score=int(validation_result_payload.get("score", 0)),
                passed_checks=passed_checks,
                failed_checks=failed_checks,
                checks_json=checks,
                recommendations_json=recommendations,
                raw_result_json=raw_result,
                created_at=created_at,
            )
        )
        return

    record.status = _enum_value(validation_result_payload.get("status"))
    record.passed = bool(validation_result_payload.get("passed", False))
    record.score = int(validation_result_payload.get("score", 0))
    record.passed_checks = passed_checks
    record.failed_checks = failed_checks
    record.checks_json = checks
    record.recommendations_json = recommendations
    record.raw_result_json = raw_result
    record.created_at = created_at


def _json_value(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")

    if isinstance(value, dict):
        return {
            str(key): _json_value(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            _json_value(item)
            for item in value
        ]

    if isinstance(value, tuple):
        return [
            _json_value(item)
            for item in value
        ]

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, Path):
        return str(value)

    if hasattr(value, "value"):
        return value.value

    return value


def _enum_value(value: Any) -> str:
    if value is None:
        return "unknown"

    if hasattr(value, "value"):
        return str(value.value)

    text = str(value)

    if "." in text:
        return text.split(".")[-1]

    return text


def _parse_datetime(value: Any) -> datetime:
    parsed = _parse_optional_datetime(value)

    if parsed is not None:
        return parsed

    return datetime.now(timezone.utc)


def _parse_optional_datetime(value: Any) -> datetime | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value

    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    return None
