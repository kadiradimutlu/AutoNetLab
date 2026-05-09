from fastapi import APIRouter, status

from app.schemas.enums import SessionStatus
from app.schemas.lab import (
    ActionResponse,
    CliAccessResponse,
    CreateLabRequest,
    LabSessionDebugResponse,
    LabSessionResponse,
)
from app.schemas.validation import ValidationResult
from app.schemas.recommendation import RecommendationResponse
from app.services.containerlab_adapter import containerlab_adapter
from app.services.session_service import (
    create_lab_session,
    get_cli_access_response,
    get_lab_session,
    to_lab_session_debug_response,
    to_lab_session_response,
    update_session_status,
    update_session_validation_result,
)
from app.services.validation_service import validate_session
from app.services.recommendation.engine import build_recommendations_for_session

router = APIRouter(prefix="/labs", tags=["Lab Sessions"])


@router.post(
    "",
    response_model=LabSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_lab(request: CreateLabRequest) -> LabSessionResponse:
    return create_lab_session(request)


@router.get("/{session_id}", response_model=LabSessionResponse)
def get_lab(session_id: str) -> LabSessionResponse:
    session = get_lab_session(session_id)

    return to_lab_session_response(
        session,
        message="Lab session retrieved successfully.",
    )

@router.get("/{session_id}/debug", response_model=LabSessionDebugResponse)
def get_lab_debug(session_id: str) -> LabSessionDebugResponse:
    session = get_lab_session(session_id)

    return to_lab_session_debug_response(
        session,
        message="Debug lab session retrieved successfully.",
    )

@router.get("/{session_id}/cli", response_model=CliAccessResponse)
def get_lab_cli_access(session_id: str) -> CliAccessResponse:
    return get_cli_access_response(session_id)


@router.post("/{session_id}/deploy", response_model=ActionResponse)
def deploy_lab(session_id: str) -> ActionResponse:
    session = get_lab_session(session_id)

    result = containerlab_adapter.deploy(
        session_id=session_id,
        topology_file=session["topology_file"],
    )

    update_session_status(session_id, result["status"])

    return ActionResponse(**result)


@router.get("/{session_id}/inspect", response_model=ActionResponse)
def inspect_lab(session_id: str) -> ActionResponse:
    session = get_lab_session(session_id)

    result = containerlab_adapter.inspect(
        session_id=session_id,
        topology_file=session["topology_file"],
        current_status=session["status"],
    )

    if result["status"] == SessionStatus.error:
        update_session_status(session_id, SessionStatus.error)

    return ActionResponse(**result)


@router.post("/{session_id}/destroy", response_model=ActionResponse)
def destroy_lab(session_id: str) -> ActionResponse:
    session = get_lab_session(session_id)

    result = containerlab_adapter.destroy(
        session_id=session_id,
        topology_file=session["topology_file"],
    )

    update_session_status(session_id, result["status"])

    return ActionResponse(**result)


@router.post("/{session_id}/validate", response_model=ValidationResult)
def validate_lab(session_id: str) -> ValidationResult:
    session = get_lab_session(session_id)

    result = validate_session(session)

    update_session_validation_result(session_id, result)

    return result


@router.get("/{session_id}/recommendations", response_model=RecommendationResponse)
def get_lab_recommendations(session_id: str) -> RecommendationResponse:
    session = get_lab_session(session_id)

    return RecommendationResponse(
        **build_recommendations_for_session(session)
    )
