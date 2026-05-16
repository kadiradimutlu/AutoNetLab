from fastapi import APIRouter, Depends, WebSocket, status

from app.core.auth import get_current_user, require_instructor
from app.schemas.auth import AuthenticatedUser
from app.schemas.enums import SessionStatus
from app.schemas.lab import (
    ActionResponse,
    CliAccessResponse,
    CreateLabRequest,
    LabSessionDebugResponse,
    LabSessionResponse,
    WebCliReadinessResponse,
)
from app.schemas.recommendation import RecommendationResponse
from app.schemas.validation import StudentValidationResult
from app.services.containerlab_adapter import containerlab_adapter
from app.services.recommendation.engine import build_recommendations_for_session
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
from app.services.web_cli_service import (
    WebCliError,
    build_web_cli_context,
    get_web_cli_readiness,
    run_web_cli_bridge,
)

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
def get_lab_debug(
    session_id: str,
    _current_user: AuthenticatedUser = Depends(require_instructor),
) -> LabSessionDebugResponse:
    session = get_lab_session(session_id)

    return to_lab_session_debug_response(
        session,
        message="Debug lab session retrieved successfully.",
    )


@router.get("/{session_id}/cli", response_model=CliAccessResponse)
def get_lab_cli_access(session_id: str) -> CliAccessResponse:
    return get_cli_access_response(session_id)


@router.get("/{session_id}/cli/readiness", response_model=WebCliReadinessResponse)
def get_lab_cli_readiness(
    session_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> WebCliReadinessResponse:
    return WebCliReadinessResponse(
        **get_web_cli_readiness(
            session_id=session_id,
            current_user=current_user,
        )
    )


@router.get("/{session_id}/cli/readiness/{device_id}", response_model=WebCliReadinessResponse)
def get_lab_device_cli_readiness(
    session_id: str,
    device_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> WebCliReadinessResponse:
    return WebCliReadinessResponse(
        **get_web_cli_readiness(
            session_id=session_id,
            device_id=device_id,
            current_user=current_user,
        )
    )


@router.websocket("/{session_id}/cli/ws/{device_id}")
async def web_cli_socket(
    websocket: WebSocket,
    session_id: str,
    device_id: str,
    token: str | None = None,
) -> None:
    await websocket.accept()

    try:
        context = build_web_cli_context(
            session_id=session_id,
            device_id=device_id,
            token=token,
        )
    except WebCliError as exc:
        await websocket.send_json(exc.to_payload())
        await websocket.close(code=exc.websocket_code)
        return

    await websocket.send_json(
        {
            "type": "connected",
            "success": True,
            "session_id": context.session_id,
            "device_id": context.device_id,
            "container_name": context.container_name,
            "mode": "browser_cli_mvp",
            "message": "Web CLI connection accepted by backend.",
        }
    )

    await run_web_cli_bridge(
        websocket=websocket,
        context=context,
    )


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

@router.post("/{session_id}/validate", response_model=StudentValidationResult)
def validate_lab(session_id: str) -> StudentValidationResult:
    session = get_lab_session(session_id)

    result = validate_session(session)

    update_session_validation_result(session_id, result)

    return StudentValidationResult(**result.model_dump(mode="json"))

@router.get("/{session_id}/recommendations", response_model=RecommendationResponse)
def get_lab_recommendations(session_id: str) -> RecommendationResponse:
    session = get_lab_session(session_id)

    return RecommendationResponse(
        **build_recommendations_for_session(session)
    )
