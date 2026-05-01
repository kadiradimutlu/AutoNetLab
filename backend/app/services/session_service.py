from uuid import uuid4

from fastapi import HTTPException, status

from app.schemas.enums import SessionStatus
from app.schemas.lab import CliAccess, CreateLabRequest, LabSessionResponse
from app.services.error_injection import generate_errors
from app.services.topology_generator import generate_session_topology


_sessions: dict[str, dict] = {}


def create_lab_session(request: CreateLabRequest) -> LabSessionResponse:
    session_id = f"lab-{uuid4().hex[:8]}"

    generated_topology = generate_session_topology(
        session_id=session_id,
        difficulty=request.difficulty,
        topology_template=request.topology_template,
    )

    topology = generated_topology["topology"]
    injected_errors = generate_errors(request.difficulty, seed=session_id)

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

    return to_lab_session_response(
        session,
        message="Lab session created successfully.",
    )


def get_lab_session(session_id: str) -> dict:
    session = _sessions.get(session_id)

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lab session '{session_id}' not found.",
        )

    return session


def update_session_status(session_id: str, new_status: SessionStatus) -> dict:
    session = get_lab_session(session_id)
    session["status"] = new_status
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
