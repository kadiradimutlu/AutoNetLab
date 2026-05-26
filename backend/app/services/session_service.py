import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload

from app.db.repositories import (
    persist_lab_session_snapshot,
    persist_validation_result_snapshot,
)
from app.db.models import LabSessionRecord
from app.db.session import session_scope
from app.schemas.enums import Difficulty, SessionStatus
from app.schemas.lab import (
    CliAccess,
    CliAccessResponse,
    CreateLabRequest,
    ErrorItem,
    LabSessionDebugResponse,
    LabSessionResponse,
)
from app.schemas.topology import Topology
from app.services.error_injection import apply_error_injection
from app.services.topology_generator import GENERATED_DIR, generate_session_topology
from app.services.recommendation.features import build_topic_performance


_sessions: dict[str, dict] = {}
logger = logging.getLogger(__name__)


BASE_STUDENT_HINTS = [
    "Check IP addressing and subnet masks.",
    "Verify interface status before testing connectivity.",
    "Review routing and default gateway configuration.",
]

DIFFICULTY_STUDENT_HINTS = {
    Difficulty.easy: [
        "Start with basic connectivity tests between directly connected devices.",
    ],
    Difficulty.medium: [
        "Compare addressing, interfaces, and routing step by step across the topology.",
    ],
    Difficulty.hard: [
        "Break the troubleshooting process into addressing, interface status, VLAN, and routing checks.",
    ],
}

ACTIVE_LAB_STATUS_VALUES = {
    SessionStatus.created.value,
    SessionStatus.deployed.value,
    SessionStatus.validated.value,
}

CLEANUP_REQUIRED_LAB_STATUS_VALUES = {
    SessionStatus.error.value,
}

BLOCKING_LAB_STATUS_VALUES = (
    ACTIVE_LAB_STATUS_VALUES
    | CLEANUP_REQUIRED_LAB_STATUS_VALUES
)

RUNTIME_ACTIVE_STATUS_VALUES = {
    SessionStatus.deployed.value,
    SessionStatus.validated.value,
}

INACTIVE_LAB_STATUS_VALUES = {
    SessionStatus.destroyed.value,
    SessionStatus.finished.value,
}

def create_lab_session(
    request: CreateLabRequest,
    authenticated_student_id: str | None = None,
) -> LabSessionResponse:
    session_id = f"lab-{uuid4().hex[:8]}"
    student_id = authenticated_student_id or request.student_id or "demo-student"

    blocking_session = find_active_lab_for_student(student_id)
    if blocking_session is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_build_blocking_lab_create_detail(blocking_session),
        )

    generated_topology = generate_session_topology(
        session_id=session_id,
        difficulty=request.difficulty,
        topology_template=request.topology_template,
    )

    topology = generated_topology["topology"]
    session_dir = Path(generated_topology["topology_file"]).parent

    topology_devices = [
        node.id
        for node in topology.nodes
    ]

    injected_errors = apply_error_injection(
        difficulty=request.difficulty,
        seed=session_id,
        session_dir=session_dir,
        topology_devices=topology_devices,
    )

    cli_access = build_cli_access(
        lab_name=generated_topology["lab_name"],
        topology=topology,
    )

    session = {
        "session_id": session_id,
        "student_id": student_id,
        "difficulty": request.difficulty,
        "status": SessionStatus.created,
        "topology": topology,
        "topology_file": generated_topology["topology_file"],
        "topology_template": generated_topology["topology_template"],
        "lab_name": generated_topology["lab_name"],
        "injected_errors": injected_errors,
        "cli_access": cli_access,
        "created_at": _utc_now_iso(),
        "completed_at": None,
        "finished_at": None,
        "validation_result": None,
        "validation_attempts": [],
        "topic_performance": None,
        "score": None,
        "passed": None,
        "runtime_cleanup_history": [],
    }

    _sessions[session_id] = session
    _save_session_metadata(session)
    persist_lab_session_snapshot(session)

    return to_lab_session_response(
        session,
        message="Lab session created successfully.",
    )


def list_lab_sessions(
    owner_student_id: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """
    Lists lab sessions DB-first.

    PostgreSQL is the primary history source for My Labs and instructor
    drilldowns. In-memory sessions and session.json metadata remain runtime
    compatibility/enrichment sources, but they must not hide older DB-backed
    history.
    """

    sessions_by_id: dict[str, dict] = _load_db_lab_sessions_by_id()

    for session_id, memory_session in list(_sessions.items()):
        if session_id in sessions_by_id:
            sessions_by_id[session_id] = _merge_session_records(
                primary=memory_session,
                fallback=sessions_by_id[session_id],
            )
        else:
            sessions_by_id[session_id] = memory_session

    if GENERATED_DIR.exists():
        for metadata_path in GENERATED_DIR.glob("*/session.json"):
            session_id = metadata_path.parent.name
            loaded_session = _load_session_metadata(session_id)

            if loaded_session is None:
                continue

            if session_id in sessions_by_id:
                sessions_by_id[session_id] = _merge_session_records(
                    primary=sessions_by_id[session_id],
                    fallback=loaded_session,
                )
            else:
                sessions_by_id[session_id] = loaded_session

            _sessions.setdefault(session_id, sessions_by_id[session_id])

    sessions = list(sessions_by_id.values())

    if owner_student_id is not None:
        sessions = [
            session
            for session in sessions
            if str(session.get("student_id")) == owner_student_id
        ]

    sessions.sort(
        key=lambda session: str(session.get("created_at") or ""),
        reverse=True,
    )

    return sessions[:limit]

def get_lab_session(session_id: str) -> dict:
    session = _sessions.get(session_id)

    if session is not None:
        return session

    session = _load_session_metadata(session_id)

    if session is None:
        session = _load_db_lab_session_metadata(session_id)

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lab session '{session_id}' not found.",
        )

    _sessions[session_id] = session
    return session


def _load_db_lab_sessions_by_id() -> dict[str, dict]:
    try:
        with session_scope() as db:
            records = (
                db.query(LabSessionRecord)
                .options(
                    joinedload(LabSessionRecord.validation_result),
                    joinedload(LabSessionRecord.validation_attempts),
                )
                .all()
            )

            return {
                str(record.session_id): _db_session_record_to_session(record)
                for record in records
            }
    except SQLAlchemyError:
        logger.warning(
            "Database lab session history read failed. Falling back to runtime/session.json sources.",
            exc_info=True,
        )
        return {}
    except Exception:
        logger.warning(
            "Unexpected lab session history read failure. Falling back to runtime/session.json sources.",
            exc_info=True,
        )
        return {}


def _load_db_lab_session_metadata(session_id: str) -> dict | None:
    try:
        with session_scope() as db:
            record = (
                db.query(LabSessionRecord)
                .options(
                    joinedload(LabSessionRecord.validation_result),
                    joinedload(LabSessionRecord.validation_attempts),
                )
                .filter(LabSessionRecord.session_id == session_id)
                .one_or_none()
            )

            if record is None:
                return None

            return _db_session_record_to_session(record)
    except SQLAlchemyError:
        logger.warning(
            "Database lab session detail read failed.",
            extra={"session_id": session_id},
            exc_info=True,
        )
        return None
    except Exception:
        logger.warning(
            "Unexpected lab session detail read failure.",
            extra={"session_id": session_id},
            exc_info=True,
        )
        return None


def _db_session_record_to_session(record: LabSessionRecord) -> dict:
    topology_payload = record.topology_json or {
        "name": record.lab_name,
        "nodes": [],
        "links": [],
    }
    topology = Topology(**topology_payload)

    cli_access_payload = list(record.cli_access_json or [])
    if cli_access_payload:
        cli_access = [
            _normalize_cli_access_item(
                raw_cli=raw_cli,
                lab_name=record.lab_name,
            )
            for raw_cli in cli_access_payload
        ]
    else:
        cli_access = build_cli_access(
            lab_name=record.lab_name,
            topology=topology,
        )

    validation_result = _db_validation_result_payload(record)
    validation_attempts = [
        _db_validation_attempt_payload(attempt)
        for attempt in list(record.validation_attempts or [])
    ]

    return {
        "session_id": record.session_id,
        "student_id": record.student_id,
        "difficulty": Difficulty(_enum_value(record.difficulty)),
        "status": SessionStatus(_enum_value(record.status)),
        "topology": topology,
        "topology_file": record.topology_file,
        "topology_template": record.topology_template,
        "lab_name": record.lab_name,
        "injected_errors": [
            ErrorItem(**error)
            for error in list(record.injected_errors_json or [])
        ],
        "cli_access": cli_access,
        "created_at": _datetime_to_iso(record.created_at),
        "completed_at": _datetime_to_iso(record.completed_at),
        "finished_at": None,
        "validation_result": validation_result,
        "validation_attempts": validation_attempts,
        "topic_performance": record.topic_performance_json,
        "score": record.score,
        "passed": record.passed,
        "runtime_cleanup_history": [],
    }


def _db_validation_result_payload(record: LabSessionRecord) -> dict | None:
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


def _db_validation_attempt_payload(record) -> dict:
    payload = dict(record.raw_result_json or {})
    payload.setdefault("attempt_number", record.attempt_number)
    payload.setdefault("session_id", record.session_id)
    payload.setdefault("status", record.status)
    payload.setdefault("passed", record.passed)
    payload.setdefault("score", record.score)
    payload.setdefault("passed_checks", record.passed_checks)
    payload.setdefault("failed_checks", record.failed_checks)
    payload.setdefault("checks", record.checks_json or [])
    payload.setdefault("recommendations", record.recommendations_json or [])
    payload.setdefault("created_at", _datetime_to_iso(record.created_at))

    return payload


def _merge_session_records(primary: dict, fallback: dict) -> dict:
    merged = dict(primary)

    enrichment_keys = (
        "finished_at",
        "validation_result",
        "validation_attempts",
        "topic_performance",
        "score",
        "passed",
        "runtime_cleanup_history",
    )

    for key in enrichment_keys:
        if _is_missing_session_value(merged.get(key)) and not _is_missing_session_value(fallback.get(key)):
            merged[key] = fallback.get(key)

    if _is_missing_session_value(merged.get("cli_access")) and not _is_missing_session_value(fallback.get("cli_access")):
        merged["cli_access"] = fallback["cli_access"]

    if _is_missing_session_value(merged.get("injected_errors")) and not _is_missing_session_value(fallback.get("injected_errors")):
        merged["injected_errors"] = fallback["injected_errors"]

    if _is_missing_session_value(merged.get("topology")) and not _is_missing_session_value(fallback.get("topology")):
        merged["topology"] = fallback["topology"]

    return merged


def _is_missing_session_value(value) -> bool:
    return value is None or value == [] or value == {}


def _datetime_to_iso(value) -> str | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.isoformat()

    return str(value)


def update_session_status(session_id: str, new_status: SessionStatus) -> dict:
    session = get_lab_session(session_id)
    session["status"] = new_status
    _save_session_metadata(session)
    persist_lab_session_snapshot(session)
    return session


def record_runtime_cleanup_result(
    session_id: str,
    trigger: str,
    cleanup_result: dict,
) -> dict:
    """
    Stores internal runtime cleanup evidence without changing the public
    student-safe lab response contract.
    """

    session = get_lab_session(session_id)

    cleanup_history = list(session.get("runtime_cleanup_history") or [])
    cleanup_history.append(
        {
            "trigger": trigger,
            "success": bool(cleanup_result.get("success")),
            "status": _enum_value(cleanup_result.get("status")),
            "message": cleanup_result.get("message"),
            "command": cleanup_result.get("command"),
            "return_code": cleanup_result.get("return_code"),
            "error_code": cleanup_result.get("error_code"),
            "stdout": cleanup_result.get("stdout"),
            "stderr": cleanup_result.get("stderr"),
            "created_at": _utc_now_iso(),
        }
    )

    session["runtime_cleanup_history"] = cleanup_history[-20:]

    _save_session_metadata(session)
    persist_lab_session_snapshot(session)

    return session


def update_session_validation_result(session_id: str, validation_result) -> dict:
    """
    Persists validation result / doÄŸrulama sonucunu session metadata iÃ§ine kaydeder.

    Sprint 6 analytics endpointleri session.json dosyalarÄ±nÄ± read-only ÅŸekilde okuyacaÄŸÄ± iÃ§in
    score, passed, checks ve recommendations alanlarÄ±nÄ±n kalÄ±cÄ± olmasÄ± gerekir.
    """

    session = get_lab_session(session_id)

    if hasattr(validation_result, "model_dump"):
        result_payload = validation_result.model_dump(mode="json")
    else:
        result_payload = dict(validation_result)

    attempt_payload = _build_validation_attempt_payload(
        session=session,
        result_payload=result_payload,
    )

    validation_attempts = list(session.get("validation_attempts") or [])
    validation_attempts.append(attempt_payload)

    result_payload["attempt_number"] = attempt_payload["attempt_number"]
    result_payload["created_at"] = attempt_payload["created_at"]
    result_payload["passed_checks"] = attempt_payload["passed_checks"]
    result_payload["failed_checks"] = attempt_payload["failed_checks"]

    session["status"] = SessionStatus.validated
    session["validation_result"] = result_payload
    session["validation_attempts"] = validation_attempts
    session["score"] = result_payload.get("score")
    session["passed"] = result_payload.get("passed")
    session["topic_performance"] = build_topic_performance(result_payload)
    session["completed_at"] = attempt_payload["created_at"]

    if not session.get("created_at"):
        session["created_at"] = _utc_now_iso()

    _save_session_metadata(session)
    persist_validation_result_snapshot(session, result_payload)
    return session


def get_cli_access_response(session_id: str) -> CliAccessResponse:
    session = get_lab_session(session_id)

    return CliAccessResponse(
        session_id=session["session_id"],
        lab_name=session["lab_name"],
        devices=session["cli_access"],
        message="CLI access information retrieved successfully.",
    )


def to_lab_session_response(session: dict, message: str) -> LabSessionResponse:
    """
    Builds student-safe response / Ã¶ÄŸrenciye gÃ¼venli yanÄ±t.

    injected_errors intentionally stays inside internal session metadata,
    but it is not exposed through the default student-facing API response.
    """

    return LabSessionResponse(
        session_id=session["session_id"],
        student_id=session["student_id"],
        difficulty=session["difficulty"],
        status=session["status"],
        score=session.get("score"),
        passed=session.get("passed"),
        created_at=session.get("created_at"),
        completed_at=session.get("completed_at"),
        finished_at=session.get("finished_at"),
        topology_summary=build_topology_summary(session),
        topology=session["topology"],
        cli_access=session["cli_access"],
        hints=build_student_hints(session["difficulty"]),
        message=message,
    )


def to_lab_session_debug_response(session: dict, message: str) -> LabSessionDebugResponse:
    """
    Builds instructor/debug response / eÄŸitmen veya debug yanÄ±tÄ±.

    This response includes injected_errors and should only be used by
    explicit debug/instructor endpoints.
    """

    return LabSessionDebugResponse(
        session_id=session["session_id"],
        student_id=session["student_id"],
        difficulty=session["difficulty"],
        status=session["status"],
        topology=session["topology"],
        cli_access=session["cli_access"],
        hints=build_student_hints(session["difficulty"]),
        injected_errors=session["injected_errors"],
        message=message,
    )



def build_topology_summary(session: dict) -> dict[str, str | int | list[str]]:
    """
    Builds a compact topology summary for lab history / My Labs screens.

    The full topology object remains in the response for the workspace view.
    This summary gives the frontend enough metadata for cards, tables, and lists
    without parsing the full topology graph each time.
    """

    topology = session.get("topology")
    nodes = list(getattr(topology, "nodes", []) or [])
    links = list(getattr(topology, "links", []) or [])

    devices = [
        _topology_item_id(node)
        for node in nodes
    ]

    topology_name = (
        getattr(topology, "name", None)
        or session.get("lab_name")
        or session.get("session_id")
        or "unknown-topology"
    )

    return {
        "name": str(topology_name),
        "node_count": len(nodes),
        "link_count": len(links),
        "devices": devices,
    }


def _topology_item_id(item: object) -> str:
    if isinstance(item, dict):
        return str(item.get("id") or item.get("name") or "unknown")

    return str(
        getattr(
            item,
            "id",
            getattr(item, "name", "unknown"),
        )
    )

def build_student_hints(difficulty: Difficulty) -> list[str]:
    """
    Returns generic troubleshooting hints / genel hata giderme ipuÃ§larÄ±.

    These hints are intentionally broad. They must not reveal exact injected
    error codes, devices, interfaces, expected fixes, or solution details.
    """

    return BASE_STUDENT_HINTS + DIFFICULTY_STUDENT_HINTS.get(difficulty, [])



def is_active_lab_status(value) -> bool:
    return _enum_value(value) in ACTIVE_LAB_STATUS_VALUES


def is_runtime_active_status(value) -> bool:
    return _enum_value(value) in RUNTIME_ACTIVE_STATUS_VALUES


def find_active_lab_for_student(student_id: str) -> dict | None:
    """
    Returns the newest lab session that blocks creating a new lab.

    Cleanup-required error sessions are intentionally prioritized over active
    runtime sessions so students are directed to clean risky runtime state
    before continuing. DB-first error lookup is intentional so historical or
    DB-backed cleanup-required sessions cannot be bypassed by direct API calls.
    """

    db_backed_sessions = list_lab_sessions(
        owner_student_id=student_id,
        limit=500,
    )

    for session in db_backed_sessions:
        if _session_status_value(session.get("status")) in CLEANUP_REQUIRED_LAB_STATUS_VALUES:
            return session

    runtime_sessions = _list_runtime_lab_sessions(
        owner_student_id=student_id,
        limit=500,
    )

    for session in runtime_sessions:
        if _session_status_value(session.get("status")) in ACTIVE_LAB_STATUS_VALUES:
            return session

    return None


def _build_blocking_lab_create_detail(session: dict) -> dict:
    session_id = str(session.get("session_id"))
    status_value = _session_status_value(session.get("status"))

    if status_value in CLEANUP_REQUIRED_LAB_STATUS_VALUES:
        return {
            "message": "You have a lab that requires runtime cleanup. Clean it up before creating a new lab.",
            "active_session_id": session_id,
            "blocking_session_id": session_id,
            "blocking_status": status_value,
            "cleanup_required": True,
        }

    return {
        "message": "You already have an active lab. Finish or close it before creating a new one.",
        "active_session_id": session_id,
        "blocking_session_id": session_id,
        "blocking_status": status_value,
        "cleanup_required": False,
    }


def _session_status_value(value) -> str:
    if hasattr(value, "value"):
        return value.value

    return str(value)


def _list_runtime_lab_sessions(
    owner_student_id: str | None = None,
    limit: int = 100,
) -> list[dict]:
    sessions_by_id: dict[str, dict] = {}

    for session_id, session in list(_sessions.items()):
        if _has_runtime_metadata(session):
            sessions_by_id[session_id] = session

    if GENERATED_DIR.exists():
        for metadata_path in GENERATED_DIR.glob("*/session.json"):
            session_id = metadata_path.parent.name
            loaded_session = _load_session_metadata(session_id)

            if loaded_session is not None:
                sessions_by_id[session_id] = loaded_session
                _sessions[session_id] = loaded_session

    sessions = list(sessions_by_id.values())

    if owner_student_id is not None:
        sessions = [
            session
            for session in sessions
            if str(session.get("student_id")) == owner_student_id
        ]

    sessions.sort(
        key=lambda session: str(session.get("created_at") or ""),
        reverse=True,
    )

    return sessions[:limit]


def _has_runtime_metadata(session: dict) -> bool:
    session_id = session.get("session_id")
    if session_id and (GENERATED_DIR / str(session_id) / "session.json").exists():
        return True

    topology_file = session.get("topology_file")
    if topology_file and Path(str(topology_file)).exists():
        return True

    return False


def finish_lab_session(session_id: str) -> dict:
    session = get_lab_session(session_id)
    finished_at = _utc_now_iso()

    session["status"] = SessionStatus.finished
    session["finished_at"] = finished_at
    session["completed_at"] = session.get("completed_at") or finished_at

    _save_session_metadata(session)
    persist_lab_session_snapshot(session)

    return session


def get_validation_history_response(session_id: str) -> dict:
    session = get_lab_session(session_id)

    return {
        "success": True,
        "session_id": session_id,
        "attempts": list(session.get("validation_attempts") or []),
        "message": "Validation history retrieved successfully.",
    }


def build_lab_hints_response(session_id: str) -> dict:
    session = get_lab_session(session_id)

    return {
        "success": True,
        "session_id": session_id,
        "hints": build_structured_student_hints(session),
        "message": "Student-safe hints retrieved successfully.",
    }


def build_structured_student_hints(session: dict) -> list[dict[str, str | None]]:
    hints: list[dict[str, str | None]] = []
    seen: set[tuple[str, str | None, str]] = set()

    for error in session.get("injected_errors", []) or []:
        topic = str(_item_value(error, "topic") or "General Troubleshooting")
        device = _item_value(error, "device")
        device_text = str(device) if device else None
        message = _topic_hint_message(topic)

        key = (topic, device_text, message)
        if key in seen:
            continue

        seen.add(key)
        hints.append(
            {
                "topic": _hint_topic_label(topic),
                "device": device_text,
                "level": "general",
                "message": message,
            }
        )

    if hints:
        return hints

    return [
        {
            "topic": "General Troubleshooting",
            "device": None,
            "level": "general",
            "message": hint,
        }
        for hint in build_student_hints(session.get("difficulty", Difficulty.easy))
    ]


def _build_validation_attempt_payload(
    session: dict,
    result_payload: dict,
) -> dict:
    checks = [
        _student_safe_check_payload(check)
        for check in result_payload.get("checks", [])
    ]

    passed_checks = sum(1 for check in checks if check.get("passed") is True)
    failed_checks = sum(1 for check in checks if check.get("passed") is False)
    previous_attempts = list(session.get("validation_attempts") or [])

    return {
        "attempt_number": len(previous_attempts) + 1,
        "session_id": session["session_id"],
        "score": int(result_payload.get("score", 0)),
        "passed": bool(result_payload.get("passed", False)),
        "passed_checks": passed_checks,
        "failed_checks": failed_checks,
        "created_at": _utc_now_iso(),
        "checks": checks,
    }


def _student_safe_check_payload(check) -> dict:
    if hasattr(check, "model_dump"):
        payload = check.model_dump(mode="json")
    else:
        payload = dict(check)

    payload.pop("evidence", None)

    return {
        "check_id": payload.get("check_id", "unknown_check"),
        "topic": payload.get("topic", "unknown"),
        "description": payload.get("description", "Validation check."),
        "status": payload.get("status", "failed"),
        "passed": bool(payload.get("passed", False)),
        "points": int(payload.get("points", 0)),
        "max_points": int(payload.get("max_points", 0)),
        "message": payload.get("message", "Validation check completed."),
        "hint": payload.get("hint"),
    }


def _item_value(item, key: str):
    if hasattr(item, key):
        return getattr(item, key)

    if isinstance(item, dict):
        return item.get(key)

    return None


def _hint_topic_label(topic: str) -> str:
    normalized = str(topic).replace("_", " ").replace("-", " ").strip()
    return normalized.title() if normalized else "General Troubleshooting"


def _topic_hint_message(topic: str) -> str:
    normalized = str(topic).lower()

    if "gateway" in normalized:
        return "Check whether the default route points to a reachable next-hop."

    if "interface" in normalized:
        return "Verify that required interfaces are administratively up and have the expected addressing."

    if "route" in normalized or "routing" in normalized:
        return "Review the routing table and confirm that the destination network has a valid path."

    if "subnet" in normalized or "address" in normalized or "ip" in normalized:
        return "Compare IP addresses and subnet masks across directly connected interfaces."

    if "vlan" in normalized:
        return "Check whether connected interfaces are placed in compatible logical segments."

    if "acl" in normalized:
        return "Review policy rules that could block expected traffic without changing unrelated connectivity."

    if "connect" in normalized:
        return "Test connectivity hop by hop and identify where traffic stops."

    return "Use show and ping-style troubleshooting to compare expected and observed network behavior."


def build_cli_access(lab_name: str, topology: Topology) -> list[CliAccess]:
    """
    Builds CLI access / CLI eriÅŸimi information for each Containerlab node.

    Containerlab container naming format:
    clab-<lab_name>-<node_id>

    Example:
    lab_name = autonetlab-lab-12345678
    node_id = r1
    container_name = clab-autonetlab-lab-12345678-r1
    """

    cli_items: list[CliAccess] = []

    for node in topology.nodes:
        container_name = f"clab-{lab_name}-{node.id}"

        cli_items.append(
            CliAccess(
                device_id=node.id,
                name=node.id,
                container_name=container_name,
                access_method="docker_exec",
                mode="local_docker_exec_demo",
                command=f"docker exec -it {container_name} sh",
                description=(
                    f"Use this command to open a CLI shell on {node.id.upper()}."
                ),
            )
        )

    return cli_items


def _save_session_metadata(session: dict) -> None:
    session_dir = Path(session["topology_file"]).parent
    session_dir.mkdir(parents=True, exist_ok=True)

    metadata_path = session_dir / "session.json"

    payload = {
        "session_id": session["session_id"],
        "student_id": session["student_id"],
        "difficulty": _enum_value(session["difficulty"]),
        "status": _enum_value(session["status"]),
        "topology": session["topology"].model_dump(),
        "topology_file": session["topology_file"],
        "topology_template": session["topology_template"],
        "lab_name": session["lab_name"],
        "injected_errors": [
            error.model_dump() if hasattr(error, "model_dump") else error
            for error in session["injected_errors"]
        ],
        "cli_access": [
            cli.model_dump() if hasattr(cli, "model_dump") else cli
            for cli in session["cli_access"]
        ],
        "created_at": session.get("created_at") or _utc_now_iso(),
        "completed_at": session.get("completed_at"),
        "finished_at": session.get("finished_at"),
        "validation_result": session.get("validation_result"),
        "validation_attempts": session.get("validation_attempts", []),
        "topic_performance": session.get("topic_performance"),
        "score": session.get("score"),
        "passed": session.get("passed"),
        "runtime_cleanup_history": session.get("runtime_cleanup_history", []),
    }

    metadata_path.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )


def _load_session_metadata(session_id: str) -> dict | None:
    if not _is_safe_session_id(session_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session_id format.",
        )

    metadata_path = GENERATED_DIR / session_id / "session.json"

    if not metadata_path.exists():
        return None

    payload = json.loads(metadata_path.read_text(encoding="utf-8"))

    topology = Topology(**payload["topology"])
    lab_name = payload["lab_name"]

    cli_access_payload = payload.get("cli_access", [])

    if cli_access_payload:
        cli_access = [
            _normalize_cli_access_item(
                raw_cli=raw_cli,
                lab_name=lab_name,
            )
            for raw_cli in cli_access_payload
        ]
    else:
        cli_access = build_cli_access(
            lab_name=lab_name,
            topology=topology,
        )

    session = {
        "session_id": payload["session_id"],
        "student_id": payload["student_id"],
        "difficulty": Difficulty(payload["difficulty"]),
        "status": SessionStatus(payload["status"]),
        "topology": topology,
        "topology_file": payload["topology_file"],
        "topology_template": payload["topology_template"],
        "lab_name": lab_name,
        "injected_errors": [
            ErrorItem(**error)
            for error in payload.get("injected_errors", [])
        ],
        "cli_access": cli_access,
        "created_at": payload.get("created_at"),
        "completed_at": payload.get("completed_at"),
        "finished_at": payload.get("finished_at"),
        "validation_result": payload.get("validation_result"),
        "validation_attempts": payload.get("validation_attempts", []),
        "topic_performance": payload.get("topic_performance"),
        "score": payload.get("score"),
        "passed": payload.get("passed"),
        "runtime_cleanup_history": payload.get("runtime_cleanup_history", []),
    }

    return session


def _normalize_cli_access_item(raw_cli: dict, lab_name: str) -> CliAccess:
    """
    Keeps backward compatibility / geriye dÃ¶nÃ¼k uyumluluk.

    Sprint 2 session.json files may only have:
    - device_id
    - command

    Sprint 3 expects:
    - device_id
    - name
    - container_name
    - access_method
    - command
    - description
    """

    device_id = raw_cli.get("device_id") or raw_cli.get("name")

    if not device_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid CLI access metadata: missing device_id.",
        )

    container_name = raw_cli.get("container_name") or f"clab-{lab_name}-{device_id}"

    return CliAccess(
        device_id=device_id,
        name=raw_cli.get("name", device_id),
        container_name=container_name,
        access_method=raw_cli.get("access_method", "docker_exec"),
        mode=raw_cli.get("mode", "local_docker_exec_demo"),
        command=raw_cli.get("command", f"docker exec -it {container_name} sh"),
        description=raw_cli.get(
            "description",
            f"Use this command to open a CLI shell on {device_id.upper()}."
        ),
    )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _enum_value(value) -> str:
    if hasattr(value, "value"):
        return value.value

    return str(value)


def _is_safe_session_id(session_id: str) -> bool:
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
    return bool(session_id) and all(char in allowed for char in session_id)
