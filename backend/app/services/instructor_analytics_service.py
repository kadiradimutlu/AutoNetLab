
import json
import logging
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from app.db.models import LabSessionRecord
from app.db.session import session_scope
from app.services.topology_generator import GENERATED_DIR


logger = logging.getLogger(__name__)

DEFAULT_DIFFICULTIES = ["easy", "medium", "hard"]

TOPIC_LABELS = {
    "ip_addressing": "IP Addressing",
    "subnetting": "Subnetting",
    "interface_status": "Interface Status",
    "routing": "Routing",
    "static_routing": "Static Routing",
    "default_gateway": "Default Gateway",
    "vlan": "VLAN",
    "vlan_like": "VLAN-like Configuration",
    "acl": "ACL",
    "acl_like": "ACL-like Policy",
    "connectivity": "Connectivity",
    "unknown": "Unknown",
}


def get_analytics_summary() -> dict:
    sessions = _load_session_records()

    total_sessions = len(sessions)
    completed_sessions = [session for session in sessions if _is_completed(session)]
    active_sessions = [
        session
        for session in sessions
        if _normalize_status(session.get("status")) in {"created", "deployed"}
    ]

    scores = [
        score
        for session in completed_sessions
        if (score := _extract_score(session)) is not None
    ]

    passed_sessions = [
        session
        for session in completed_sessions
        if _extract_passed(session) is True
    ]

    average_score = _safe_average(scores)
    pass_rate = (
        round((len(passed_sessions) / len(completed_sessions)) * 100, 2)
        if completed_sessions
        else 0.0
    )

    return {
        "success": True,
        "total_sessions": total_sessions,
        "completed_sessions": len(completed_sessions),
        "active_sessions": len(active_sessions),
        "passed_sessions": len(passed_sessions),
        "average_score": average_score,
        "pass_rate": pass_rate,
        "message": "Instructor analytics summary generated successfully.",
    }


def get_difficulty_distribution() -> dict:
    sessions = _load_session_records()

    distribution_by_difficulty = {
        difficulty: {
            "difficulty": difficulty,
            "session_count": 0,
            "completed_count": 0,
            "scores": [],
        }
        for difficulty in DEFAULT_DIFFICULTIES
    }

    for session in sessions:
        difficulty = _normalize_difficulty(session.get("difficulty"))

        if difficulty not in distribution_by_difficulty:
            distribution_by_difficulty[difficulty] = {
                "difficulty": difficulty,
                "session_count": 0,
                "completed_count": 0,
                "scores": [],
            }

        distribution_by_difficulty[difficulty]["session_count"] += 1

        if _is_completed(session):
            distribution_by_difficulty[difficulty]["completed_count"] += 1

        score = _extract_score(session)
        if score is not None:
            distribution_by_difficulty[difficulty]["scores"].append(score)

    distribution = []

    for difficulty, item in distribution_by_difficulty.items():
        distribution.append(
            {
                "difficulty": difficulty,
                "session_count": item["session_count"],
                "completed_count": item["completed_count"],
                "average_score": _safe_average(item["scores"]),
            }
        )

    distribution.sort(
        key=lambda item: (
            DEFAULT_DIFFICULTIES.index(item["difficulty"])
            if item["difficulty"] in DEFAULT_DIFFICULTIES
            else 99
        )
    )

    return {
        "success": True,
        "distribution": distribution,
        "message": "Difficulty distribution generated successfully.",
    }


def get_topic_weaknesses() -> dict:
    sessions = _load_session_records()
    topic_weaknesses = _build_topic_weaknesses(sessions)

    return {
        "success": True,
        "topic_weaknesses": topic_weaknesses,
        "message": "Topic weakness analytics generated successfully.",
    }


def get_recent_sessions(limit: int = 10) -> dict:
    sessions = _load_session_records()

    sorted_sessions = sorted(
        sessions,
        key=_sort_timestamp,
        reverse=True,
    )

    recent_sessions = [
        _session_to_recent_item(session)
        for session in sorted_sessions[:limit]
    ]

    return {
        "success": True,
        "recent_sessions": recent_sessions,
        "message": "Recent lab sessions retrieved successfully.",
    }


def get_students(limit: int = 100) -> dict:
    sessions = _load_session_records()

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for session in sessions:
        student_id = _normalize_student_id(session.get("student_id"))
        grouped[student_id].append(session)

    students = []

    for student_id, student_sessions in grouped.items():
        completed_sessions = [
            session
            for session in student_sessions
            if _is_completed(session)
        ]
        active_sessions = [
            session
            for session in student_sessions
            if _normalize_status(session.get("status")) in {"created", "deployed"}
        ]
        scores = [
            score
            for session in completed_sessions
            if (score := _extract_score(session)) is not None
        ]
        passed_sessions = [
            session
            for session in completed_sessions
            if _extract_passed(session) is True
        ]

        pass_rate = (
            round((len(passed_sessions) / len(completed_sessions)) * 100, 2)
            if completed_sessions
            else 0.0
        )

        students.append(
            {
                "student_id": student_id,
                "total_sessions": len(student_sessions),
                "completed_sessions": len(completed_sessions),
                "active_sessions": len(active_sessions),
                "average_score": _safe_average(scores),
                "pass_rate": pass_rate,
                "last_activity_at": _latest_activity(student_sessions),
            }
        )

    students.sort(
        key=lambda item: item.get("last_activity_at") or "",
        reverse=True,
    )

    return {
        "success": True,
        "students": students[:limit],
        "message": "Instructor student list generated successfully.",
    }


def get_student_summary(student_id: str) -> dict:
    student_sessions = _get_sessions_for_student(student_id)

    completed_sessions = [
        session
        for session in student_sessions
        if _is_completed(session)
    ]
    active_sessions = [
        session
        for session in student_sessions
        if _normalize_status(session.get("status")) in {"created", "deployed"}
    ]
    passed_sessions = [
        session
        for session in completed_sessions
        if _extract_passed(session) is True
    ]
    scores = [
        score
        for session in completed_sessions
        if (score := _extract_score(session)) is not None
    ]

    pass_rate = (
        round((len(passed_sessions) / len(completed_sessions)) * 100, 2)
        if completed_sessions
        else 0.0
    )

    return {
        "success": True,
        "student_id": student_id,
        "total_sessions": len(student_sessions),
        "completed_sessions": len(completed_sessions),
        "active_sessions": len(active_sessions),
        "passed_sessions": len(passed_sessions),
        "average_score": _safe_average(scores),
        "pass_rate": pass_rate,
        "first_seen_at": _first_activity(student_sessions),
        "last_activity_at": _latest_activity(student_sessions),
        "message": "Student analytics summary generated successfully.",
    }


def get_student_sessions(student_id: str, limit: int = 50) -> dict:
    student_sessions = _get_sessions_for_student(student_id)

    sorted_sessions = sorted(
        student_sessions,
        key=_sort_timestamp,
        reverse=True,
    )

    sessions = [
        _session_to_recent_item(session)
        for session in sorted_sessions[:limit]
    ]

    return {
        "success": True,
        "student_id": student_id,
        "sessions": sessions,
        "message": "Student lab sessions retrieved successfully.",
    }


def get_student_topic_weaknesses(student_id: str) -> dict:
    student_sessions = _get_sessions_for_student(student_id)
    topic_weaknesses = _build_topic_weaknesses(student_sessions)

    return {
        "success": True,
        "student_id": student_id,
        "topic_weaknesses": topic_weaknesses,
        "message": "Student topic weakness analytics generated successfully.",
    }


def get_student_score_trend(student_id: str, limit: int = 50) -> dict:
    student_sessions = _get_sessions_for_student(student_id)

    completed_or_scored_sessions = [
        session
        for session in student_sessions
        if _is_completed(session) or _extract_score(session) is not None
    ]

    sorted_sessions = sorted(
        completed_or_scored_sessions,
        key=_sort_timestamp,
    )

    score_trend = [
        {
            "session_id": session.get("session_id", "unknown"),
            "difficulty": _normalize_difficulty(session.get("difficulty")),
            "status": _normalize_status(session.get("status")),
            "score": _extract_score(session),
            "passed": _extract_passed(session),
            "created_at": session.get("created_at"),
            "completed_at": session.get("completed_at"),
        }
        for session in sorted_sessions[-limit:]
    ]

    return {
        "success": True,
        "student_id": student_id,
        "score_trend": score_trend,
        "message": "Student score trend generated successfully.",
    }


def _load_session_records() -> list[dict[str, Any]]:
    """
    Loads instructor analytics records DB-first.

    PostgreSQL/SQL is now the primary analytics source. The existing
    session.json files remain a compatibility fallback for local tests,
    older sessions, and DB outage recovery.
    """

    db_sessions = _load_db_session_records()

    if db_sessions:
        return db_sessions

    return _load_file_session_records()


def _load_db_session_records() -> list[dict[str, Any]]:
    try:
        with session_scope() as db:
            records = (
                db.query(LabSessionRecord)
                .options(joinedload(LabSessionRecord.validation_result))
                .all()
            )

            return [
                _session_record_to_payload(record)
                for record in records
            ]
    except SQLAlchemyError:
        logger.warning("Database analytics read failed. Falling back to session.json.", exc_info=True)
        return []
    except Exception:
        logger.warning("Unexpected analytics database read failure. Falling back to session.json.", exc_info=True)
        return []


def _session_record_to_payload(record: LabSessionRecord) -> dict[str, Any]:
    validation_result = _validation_record_to_payload(record)

    return {
        "session_id": record.session_id,
        "student_id": record.student_id,
        "difficulty": record.difficulty,
        "status": record.status,
        "topology": record.topology_json or {},
        "topology_file": record.topology_file,
        "topology_template": record.topology_template,
        "lab_name": record.lab_name,
        "injected_errors": record.injected_errors_json or [],
        "cli_access": record.cli_access_json or [],
        "created_at": _datetime_to_iso(record.created_at),
        "completed_at": _datetime_to_iso(record.completed_at),
        "validation_result": validation_result,
        "topic_performance": record.topic_performance_json,
        "score": record.score,
        "passed": record.passed,
        "source": "database",
    }


def _validation_record_to_payload(record: LabSessionRecord) -> dict[str, Any] | None:
    validation_record = record.validation_result

    if validation_record is None:
        return None

    payload = dict(validation_record.raw_result_json or {})

    payload.setdefault("success", True)
    payload.setdefault("session_id", validation_record.session_id)
    payload.setdefault("status", validation_record.status)
    payload.setdefault("passed", validation_record.passed)
    payload.setdefault("score", validation_record.score)
    payload.setdefault("checks", validation_record.checks_json or [])
    payload.setdefault("recommendations", validation_record.recommendations_json or [])

    return payload


def _load_file_session_records() -> list[dict[str, Any]]:
    if not GENERATED_DIR.exists():
        return []

    sessions: list[dict[str, Any]] = []

    for metadata_path in GENERATED_DIR.glob("*/session.json"):
        payload = _read_json(metadata_path)

        if not payload:
            continue

        payload.setdefault("created_at", _file_timestamp(metadata_path))
        payload.setdefault("completed_at", None)
        payload.setdefault("source", "session_json")

        sessions.append(payload)

    return sessions


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _extract_validation_result(session: dict[str, Any]) -> dict[str, Any] | None:
    validation_result = session.get("validation_result")

    if isinstance(validation_result, dict):
        return validation_result

    return None


def _extract_score(session: dict[str, Any]) -> int | None:
    score = session.get("score")

    if isinstance(score, int):
        return score

    validation_result = _extract_validation_result(session)

    if validation_result and isinstance(validation_result.get("score"), int):
        return validation_result["score"]

    return None


def _extract_passed(session: dict[str, Any]) -> bool | None:
    passed = session.get("passed")

    if isinstance(passed, bool):
        return passed

    validation_result = _extract_validation_result(session)

    if validation_result and isinstance(validation_result.get("passed"), bool):
        return validation_result["passed"]

    return None


def _is_completed(session: dict[str, Any]) -> bool:
    if _extract_validation_result(session) is not None:
        return True

    return _normalize_status(session.get("status")) == "validated"


def _normalize_difficulty(value: Any) -> str:
    if value is None:
        return "unknown"

    text = str(value).lower().strip()

    if "." in text:
        text = text.split(".")[-1]

    return text


def _normalize_status(value: Any) -> str:
    if value is None:
        return "unknown"

    text = str(value).lower().strip()

    if "." in text:
        text = text.split(".")[-1]

    return text


def _normalize_topic(value: Any) -> str:
    if value is None:
        return "unknown"

    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = text.strip("_")

    if text in {"routing", "static_route", "static_routes"}:
        return "static_routing"

    if text in {"vlan", "vlan_mismatch"}:
        return "vlan_like"

    if text in {"acl", "access_control", "access_control_list"}:
        return "acl_like"

    return text or "unknown"


def _build_topic_weaknesses(sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    topic_stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "topic": "unknown",
            "label": "Unknown",
            "fail_count": 0,
            "attempt_count": 0,
            "scores": [],
        }
    )

    for session in sessions:
        validation_result = _extract_validation_result(session)

        if not validation_result:
            continue

        score = _extract_score(session)

        for check in validation_result.get("checks", []):
            raw_topic = check.get("topic", "unknown")
            topic_key = _normalize_topic(raw_topic)

            topic_stats[topic_key]["topic"] = topic_key
            topic_stats[topic_key]["label"] = TOPIC_LABELS.get(topic_key, raw_topic)
            topic_stats[topic_key]["attempt_count"] += 1

            if score is not None:
                topic_stats[topic_key]["scores"].append(score)

            if check.get("passed") is False:
                topic_stats[topic_key]["fail_count"] += 1

    topic_weaknesses = []

    for topic_key, stats in topic_stats.items():
        attempt_count = stats["attempt_count"]
        fail_count = stats["fail_count"]
        failure_rate = round((fail_count / attempt_count) * 100, 2) if attempt_count else 0.0

        topic_weaknesses.append(
            {
                "topic": topic_key,
                "label": stats["label"],
                "fail_count": fail_count,
                "attempt_count": attempt_count,
                "failure_rate": failure_rate,
                "average_score": _safe_average(stats["scores"]),
                "severity": _severity_from_failure_rate(failure_rate),
            }
        )

    topic_weaknesses.sort(
        key=lambda item: (item["fail_count"], item["failure_rate"]),
        reverse=True,
    )

    return topic_weaknesses


def _safe_average(values: list[int | float]) -> float:
    if not values:
        return 0.0

    return round(sum(values) / len(values), 2)


def _severity_from_failure_rate(failure_rate: float) -> str:
    if failure_rate >= 60:
        return "high"

    if failure_rate >= 30:
        return "medium"

    return "low"


def _file_timestamp(path: Path) -> str:
    timestamp = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return timestamp.isoformat()


def _datetime_to_iso(value: datetime | None) -> str | None:
    if value is None:
        return None

    return value.isoformat()


def _sort_timestamp(session: dict[str, Any]) -> str:
    return session.get("completed_at") or session.get("created_at") or ""


def _get_sessions_for_student(student_id: str) -> list[dict[str, Any]]:
    requested_student_id = _normalize_student_id(student_id)

    return [
        session
        for session in _load_session_records()
        if _normalize_student_id(session.get("student_id")) == requested_student_id
    ]


def _normalize_student_id(value: Any) -> str:
    if value is None:
        return "unknown"

    text = str(value).strip()

    return text or "unknown"


def _session_to_recent_item(session: dict[str, Any]) -> dict:
    return {
        "session_id": session.get("session_id", "unknown"),
        "student_id": _normalize_student_id(session.get("student_id")),
        "difficulty": _normalize_difficulty(session.get("difficulty")),
        "status": _normalize_status(session.get("status")),
        "score": _extract_score(session),
        "passed": _extract_passed(session),
        "created_at": session.get("created_at"),
        "completed_at": session.get("completed_at"),
    }


def _first_activity(sessions: list[dict[str, Any]]) -> str | None:
    timestamps = [
        timestamp
        for session in sessions
        if (timestamp := (session.get("created_at") or session.get("completed_at")))
    ]

    return min(timestamps) if timestamps else None


def _latest_activity(sessions: list[dict[str, Any]]) -> str | None:
    timestamps = [
        timestamp
        for session in sessions
        if (timestamp := (session.get("completed_at") or session.get("created_at")))
    ]

    return max(timestamps) if timestamps else None
