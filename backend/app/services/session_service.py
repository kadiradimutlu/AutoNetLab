import json
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status

from app.schemas.enums import Difficulty, SessionStatus
from app.schemas.lab import CliAccess, CreateLabRequest, ErrorItem, LabSessionResponse
from app.schemas.topology import Topology
from app.services.error_injection import apply_error_injection
from app.services.topology_generator import GENERATED_DIR, generate_session_topology


_sessions: dict[str, dict] = {}


def create_lab_session(request: CreateLabRequest) -> LabSessionResponse:
    session_id = f"lab-{uuid4().hex[:8]}"

    generated_topology = generate_session_topology(
        session_id=session_id,
        difficulty=request.difficulty,
        topology_template=request.topology_template,
    )

    topology = generated_topology["topology"]
    session_dir = Path(generated_topology["topology_file"]).parent

    injected_errors = apply_error_injection(
        difficulty=request.difficulty,
        seed=session_id,
        session_dir=session_dir,
    )

    cli_access = [
        CliAccess(
            device_id=node.id,
            command=f"docker exec -it clab-{topology.name}-{node.id} sh",
        )
        for node in topology.nodes
    ]

    session = {
        "session_id": session_id,
        "student_id": request.student_id,
        "difficulty": request.difficulty,
        "status": SessionStatus.created,
        "topology": topology,
        "topology_file": generated_topology["topology_file"],
        "topology_template": generated_topology["topology_template"],
        "lab_name": generated_topology["lab_name"],
        "injected_errors": injected_errors,
        "cli_access": cli_access,
    }

    _sessions[session_id] = session
    _save_session_metadata(session)

    return to_lab_session_response(
        session,
        message="Lab session created successfully.",
    )


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
    return session


def to_lab_session_response(session: dict, message: str) -> LabSessionResponse:
    return LabSessionResponse(
        session_id=session["session_id"],
        student_id=session["student_id"],
        difficulty=session["difficulty"],
        status=session["status"],
        topology=session["topology"],
        injected_errors=session["injected_errors"],
        cli_access=session["cli_access"],
        message=message,
    )


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

    session = {
        "session_id": payload["session_id"],
        "student_id": payload["student_id"],
        "difficulty": Difficulty(payload["difficulty"]),
        "status": SessionStatus(payload["status"]),
        "topology": Topology(**payload["topology"]),
        "topology_file": payload["topology_file"],
        "topology_template": payload["topology_template"],
        "lab_name": payload["lab_name"],
        "injected_errors": [
            ErrorItem(**error)
            for error in payload.get("injected_errors", [])
        ],
        "cli_access": [
            CliAccess(**cli)
            for cli in payload.get("cli_access", [])
        ],
    }

    return session


def _enum_value(value) -> str:
    if hasattr(value, "value"):
        return value.value

    return str(value)


def _is_safe_session_id(session_id: str) -> bool:
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
    return bool(session_id) and all(char in allowed for char in session_id)
