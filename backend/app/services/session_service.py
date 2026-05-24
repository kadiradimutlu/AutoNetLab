import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status

from app.db.repositories import (
    persist_lab_session_snapshot,
    persist_validation_result_snapshot,
)
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

def create_lab_session(
    request: CreateLabRequest,
    authenticated_student_id: str | None = None,
) -> LabSessionResponse:
    session_id = f"lab-{uuid4().hex[:8]}"
    student_id = authenticated_student_id or request.student_id or "demo-student"

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
        "validation_result": None,
        "topic_performance": None,
        "score": None,
        "passed": None,
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
    sessions_by_id: dict[str, dict] = dict(_sessions)

    if GENERATED_DIR.exists():
        for metadata_path in GENERATED_DIR.glob("*/session.json"):
            session_id = metadata_path.parent.name

            if session_id in sessions_by_id:
                continue

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

def get_lab_session(session_id: str) -> dict:
    session = _sessions.get(session_id)

    if session is not None:
        return session

    session = _load_session_metadata(session_id)

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lab session '{session_id}' not found.",
        )

    _sessions[session_id] = session
    return session


def update_session_status(session_id: str, new_status: SessionStatus) -> dict:
    session = get_lab_session(session_id)
    session["status"] = new_status
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

    session["status"] = SessionStatus.validated
    session["validation_result"] = result_payload
    session["score"] = result_payload.get("score")
    session["passed"] = result_payload.get("passed")
    session["topic_performance"] = build_topic_performance(result_payload)
    session["completed_at"] = _utc_now_iso()

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
        "validation_result": session.get("validation_result"),
        "topic_performance": session.get("topic_performance"),
        "score": session.get("score"),
        "passed": session.get("passed"),
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
        "validation_result": payload.get("validation_result"),
        "topic_performance": payload.get("topic_performance"),
        "score": payload.get("score"),
        "passed": payload.get("passed"),
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
