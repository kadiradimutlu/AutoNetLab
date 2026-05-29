import logging

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, status

from app.core.auth import get_current_user, get_optional_current_user, require_instructor
from app.schemas.auth import AuthenticatedUser
from app.schemas.enums import SessionStatus
from app.schemas.lab import (
    ActionResponse,
    CliAccessResponse,
    CreateLabRequest,
    LabHintsResponse,
    LabSessionDebugResponse,
    LabSessionListResponse,
    LabSessionResponse,
    WebCliReadinessResponse,
)
from app.schemas.recommendation import RecommendationResponse
from app.schemas.validation import StudentValidationResult, ValidationHistoryResponse
from app.services.containerlab_adapter import containerlab_adapter
from app.services.recommendation.engine import build_recommendations_for_session
from app.services.runtime_error_injection import apply_runtime_error_injection
from app.services.scenario_catalog import is_deploy_only_scenario, is_srlinux_scenario
from app.services.srlinux_runtime_setup import apply_srlinux_runtime_setup
from app.services.session_service import (
    build_lab_hints_response,
    create_lab_session,
    finish_lab_session,
    get_cli_access_response,
    get_validation_history_response,
    get_lab_session,
    list_lab_sessions,
    record_runtime_cleanup_result,
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
logger = logging.getLogger(__name__)


@router.post(
    "",
    response_model=LabSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_lab(
    request: CreateLabRequest,
    current_user: AuthenticatedUser | None = Depends(get_optional_current_user),
) -> LabSessionResponse:
    authenticated_student_id = None

    if current_user is not None and current_user.role == "student":
        authenticated_student_id = current_user.username

    return create_lab_session(
        request=request,
        authenticated_student_id=authenticated_student_id,
    )


@router.get("", response_model=LabSessionListResponse)
def get_labs(
    student_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> LabSessionListResponse:
    owner_student_id = student_id

    if current_user.role == "student":
        owner_student_id = current_user.username

    sessions = list_lab_sessions(
        owner_student_id=owner_student_id,
        limit=limit,
    )

    responses = [
        to_lab_session_response(
            session,
            message="Lab session listed successfully.",
        )
        for session in sessions
    ]

    return LabSessionListResponse(
        sessions=responses,
        count=len(responses),
        message="Lab sessions retrieved successfully.",
    )


@router.get("/{session_id}", response_model=LabSessionResponse)
def get_lab(
    session_id: str,
    current_user: AuthenticatedUser | None = Depends(get_optional_current_user),
) -> LabSessionResponse:
    session = _get_authorized_lab_session(
        session_id=session_id,
        current_user=current_user,
    )

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
def get_lab_cli_access(
    session_id: str,
    current_user: AuthenticatedUser | None = Depends(get_optional_current_user),
) -> CliAccessResponse:
    _get_authorized_lab_session(
        session_id=session_id,
        current_user=current_user,
    )

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
def deploy_lab(
    session_id: str,
    current_user: AuthenticatedUser | None = Depends(get_optional_current_user),
) -> ActionResponse:
    session = _get_authorized_lab_session(
        session_id=session_id,
        current_user=current_user,
    )

    result = containerlab_adapter.deploy(
        session_id=session_id,
        topology_file=session["topology_file"],
    )

    if result["success"]:
        if _is_deploy_only_session(session):
            result["message"] = (
                result["message"]
                + " Scenario deployed in foundation mode without runtime fault injection."
            )
        else:
            if _is_srlinux_session(session):
                runtime_result = apply_srlinux_runtime_setup(session)
                runtime_success_message = "SR Linux runtime setup applied successfully."
            else:
                runtime_result = apply_runtime_error_injection(session)
                runtime_success_message = "Runtime error injection applied successfully."

            if not runtime_result["success"]:
                runtime_result = _attempt_runtime_cleanup_after_deploy_failure(
                    session=session,
                    failure_result=runtime_result,
                )
                update_session_status(session_id, runtime_result["status"])
                return ActionResponse(**runtime_result)

            result["message"] = (
                result["message"]
                + f" {runtime_success_message}"
            )
            result["stdout"] = "\n\n".join(
                value
                for value in [
                    result.get("stdout", ""),
                    runtime_result.get("stdout", ""),
                ]
                if value
            )
            result["stderr"] = "\n\n".join(
                value
                for value in [
                    result.get("stderr", ""),
                    runtime_result.get("stderr", ""),
                ]
                if value
            )

    update_session_status(session_id, result["status"])

    return ActionResponse(**result)


@router.get("/{session_id}/inspect", response_model=ActionResponse)
def inspect_lab(
    session_id: str,
    current_user: AuthenticatedUser | None = Depends(get_optional_current_user),
) -> ActionResponse:
    session = _get_authorized_lab_session(
        session_id=session_id,
        current_user=current_user,
    )

    result = containerlab_adapter.inspect(
        session_id=session_id,
        topology_file=session["topology_file"],
        current_status=session["status"],
    )

    if result["status"] == SessionStatus.error:
        update_session_status(session_id, SessionStatus.error)

    return ActionResponse(**result)


@router.post("/{session_id}/destroy", response_model=ActionResponse)
def destroy_lab(
    session_id: str,
    current_user: AuthenticatedUser | None = Depends(get_optional_current_user),
) -> ActionResponse:
    session = _get_authorized_lab_session(
        session_id=session_id,
        current_user=current_user,
    )

    result = containerlab_adapter.destroy(
        session_id=session_id,
        topology_file=session["topology_file"],
    )

    if _should_fallback_destroy_runtime_containers(
        session=session,
        result=result,
    ):
        result = containerlab_adapter.destroy_runtime_containers(session)
    elif _is_historical_error_cleanup_already_complete(
        session=session,
        result=result,
    ):
        result = _historical_error_cleanup_completed_response(
            session_id=session_id,
            result=result,
        )

    update_session_status(session_id, result["status"])

    return ActionResponse(**result)


def _should_fallback_destroy_runtime_containers(
    session: dict,
    result: dict,
) -> bool:
    if not _is_topology_file_missing_destroy_result(result):
        return False

    return containerlab_adapter.runtime_containers_exist(session)


def _is_topology_file_missing_destroy_result(result: dict) -> bool:
    return (
        not bool(result.get("success"))
        and result.get("error_code") == "TOPOLOGY_FILE_NOT_FOUND"
    )


def _is_historical_error_cleanup_already_complete(
    session: dict,
    result: dict,
) -> bool:
    if not _is_topology_file_missing_destroy_result(result):
        return False

    if _session_status_value(session.get("status")) != SessionStatus.error.value:
        return False

    return not containerlab_adapter.runtime_containers_exist(session)


def _historical_error_cleanup_completed_response(
    session_id: str,
    result: dict,
) -> dict:
    return {
        "success": True,
        "session_id": session_id,
        "status": SessionStatus.destroyed,
        "message": (
            "Historical error-state lab cleanup is already complete. "
            "Topology metadata is missing and no runtime containers were found."
        ),
        "command": result.get("command"),
        "return_code": result.get("return_code"),
        "stdout": result.get("stdout") or "",
        "stderr": result.get("stderr") or "",
        "error_code": None,
        "detail": None,
        "suggestion": None,
    }


def _session_status_value(value) -> str:
    if hasattr(value, "value"):
        return value.value

    return str(value)


@router.post("/{session_id}/validate", response_model=StudentValidationResult)
def validate_lab(
    session_id: str,
    current_user: AuthenticatedUser | None = Depends(get_optional_current_user),
) -> StudentValidationResult:
    session = _get_authorized_lab_session(
        session_id=session_id,
        current_user=current_user,
    )

    result = validate_session(session)

    update_session_validation_result(session_id, result)

    return StudentValidationResult(**result.model_dump(mode="json"))


@router.get("/{session_id}/validation-history", response_model=ValidationHistoryResponse)
def get_lab_validation_history(
    session_id: str,
    current_user: AuthenticatedUser | None = Depends(get_optional_current_user),
) -> ValidationHistoryResponse:
    _get_authorized_lab_session(
        session_id=session_id,
        current_user=current_user,
    )

    return ValidationHistoryResponse(
        **get_validation_history_response(session_id)
    )


@router.get("/{session_id}/hints", response_model=LabHintsResponse)
def get_lab_hints(
    session_id: str,
    current_user: AuthenticatedUser | None = Depends(get_optional_current_user),
) -> LabHintsResponse:
    _get_authorized_lab_session(
        session_id=session_id,
        current_user=current_user,
    )

    return LabHintsResponse(
        **build_lab_hints_response(session_id)
    )


@router.post("/{session_id}/finish", response_model=ActionResponse)
def finish_lab(
    session_id: str,
    current_user: AuthenticatedUser | None = Depends(get_optional_current_user),
) -> ActionResponse:
    session = _get_authorized_lab_session(
        session_id=session_id,
        current_user=current_user,
    )

    result = containerlab_adapter.destroy(
        session_id=session_id,
        topology_file=session["topology_file"],
    )

    if not result["success"]:
        update_session_status(session_id, result["status"])
        return ActionResponse(**result)

    finished_session = finish_lab_session(session_id)

    result["status"] = finished_session["status"]
    result["message"] = "Lab finished successfully. Validation history is preserved."

    return ActionResponse(**result)


@router.get("/{session_id}/recommendations", response_model=RecommendationResponse)
def get_lab_recommendations(
    session_id: str,
    current_user: AuthenticatedUser | None = Depends(get_optional_current_user),
) -> RecommendationResponse:
    session = _get_authorized_lab_session(
        session_id=session_id,
        current_user=current_user,
    )

    return RecommendationResponse(
        **build_recommendations_for_session(session)
    )



def _is_deploy_only_session(session: dict) -> bool:
    scenario = session.get("scenario")

    if isinstance(scenario, dict):
        return is_deploy_only_scenario(scenario.get("id"))

    return False


def _is_srlinux_session(session: dict) -> bool:
    scenario = session.get("scenario")

    if isinstance(scenario, dict):
        return is_srlinux_scenario(scenario.get("id"))

    return False


def _attempt_runtime_cleanup_after_deploy_failure(
    session: dict,
    failure_result: dict,
) -> dict:
    """
    Best-effort cleanup for the edge case where Containerlab deploy succeeds
    but runtime setup/error injection fails afterwards.

    The API still reports the lifecycle operation as failed, but the backend
    attempts to remove any already-started Containerlab runtime so error-state
    labs do not leave orphan Docker containers behind.
    """

    session_id = str(session["session_id"])
    cleanup_result = containerlab_adapter.destroy(
        session_id=session_id,
        topology_file=session["topology_file"],
    )

    record_runtime_cleanup_result(
        session_id=session_id,
        trigger="runtime_setup_failed_after_deploy",
        cleanup_result=cleanup_result,
    )

    cleaned = bool(cleanup_result.get("success"))
    cleanup_summary = (
        "Runtime cleanup after failed deploy: completed successfully."
        if cleaned
        else (
            "Runtime cleanup after failed deploy: attempted but failed "
            f"({cleanup_result.get('error_code') or 'UNKNOWN_CLEANUP_ERROR'})."
        )
    )

    logger_method = logger.warning if cleaned else logger.error
    logger_method(
        "Runtime setup failed after Containerlab deploy; cleanup result recorded.",
        extra={
            "session_id": session_id,
            "cleanup_success": cleaned,
            "cleanup_error_code": cleanup_result.get("error_code"),
            "cleanup_return_code": cleanup_result.get("return_code"),
        },
    )

    response = dict(failure_result)
    response["status"] = SessionStatus.error
    response["message"] = (
        "Containerlab deployed, but runtime setup failed. Runtime cleanup was completed."
        if cleaned
        else (
            "Containerlab deployed, but runtime setup failed. "
            "Runtime cleanup was attempted but did not complete."
        )
    )
    response["stderr"] = "\n\n".join(
        value
        for value in [
            str(response.get("stderr") or "").strip(),
            cleanup_summary,
        ]
        if value
    )
    response["suggestion"] = (
        "Create a new lab session and retry deployment. If the problem persists, check backend runtime logs."
        if cleaned
        else (
            "Use Destroy/Finish to retry cleanup, then check Docker and Containerlab state "
            "if resources remain."
        )
    )

    return response


def _get_authorized_lab_session(
    session_id: str,
    current_user: AuthenticatedUser | None,
) -> dict:
    session = get_lab_session(session_id)

    _authorize_lab_session_access(
        session=session,
        current_user=current_user,
    )

    return session


def _authorize_lab_session_access(
    session: dict,
    current_user: AuthenticatedUser | None,
) -> None:
    # Backward compatibility:
    # Existing demo/body-based API calls without Authorization are still allowed.
    # Real ownership protection is enforced whenever an authenticated user is present.
    if current_user is None:
        return

    if current_user.role == "instructor":
        return

    allowed_student_ids = {
        current_user.username,
    }

    if current_user.student_id:
        allowed_student_ids.add(current_user.student_id)

    session_student_id = str(session.get("student_id", ""))

    if session_student_id not in allowed_student_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student users may only access their own lab sessions.",
        )
