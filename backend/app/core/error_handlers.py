from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def register_exception_handlers(app) -> None:
    """
    Registers global exception handlers / genel hata yakalayıcıları.

    Goal:
    - Keep backend stable when errors occur.
    - Return frontend-friendly JSON error responses.
    - Avoid exposing raw FastAPI default error shape directly to the dashboard.
    """

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        detail = _normalize_detail(exc.detail)

        error_code, message, suggestion = _classify_http_error(
            status_code=exc.status_code,
            detail=detail,
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error_code": error_code,
                "message": message,
                "detail": detail,
                "suggestion": suggestion,
                "path": request.url.path,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        errors = exc.errors()
        error_code, message, suggestion = _classify_validation_error(errors)

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error_code": error_code,
                "message": message,
                "detail": errors,
                "suggestion": suggestion,
                "path": request.url.path,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error_code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected backend error occurred.",
                "detail": str(exc),
                "suggestion": (
                    "Check the backend logs. If the problem is related to Docker or Containerlab, "
                    "verify Docker Desktop, WSL2 integration, and Containerlab installation."
                ),
                "path": request.url.path,
            },
        )


def _normalize_detail(detail: Any) -> Any:
    if detail is None:
        return "No additional error detail provided."

    return detail


def _classify_http_error(
    status_code: int,
    detail: Any,
) -> tuple[str, str, str]:
    detail_text = str(detail).lower()

    if status_code == status.HTTP_404_NOT_FOUND:
        if "lab session" in detail_text and "not found" in detail_text:
            return (
                "LAB_SESSION_NOT_FOUND",
                "Requested lab session could not be found.",
                "Check the session_id or create a new lab session.",
            )

        if "topology file" in detail_text and "not found" in detail_text:
            return (
                "TOPOLOGY_FILE_NOT_FOUND",
                "Topology YAML file could not be found.",
                "Create the lab session again or check the generated Containerlab topology file.",
            )

        return (
            "RESOURCE_NOT_FOUND",
            "Requested resource could not be found.",
            "Check the URL, identifier, or request parameters.",
        )

    if status_code == status.HTTP_400_BAD_REQUEST:
        if "invalid session_id" in detail_text:
            return (
                "INVALID_SESSION_ID",
                "Invalid session_id format.",
                "Use a valid lab session id such as lab-12345678.",
            )

        if "topology file" in detail_text:
            return (
                "INVALID_TOPOLOGY_FILE",
                "Topology YAML file is invalid.",
                "Make sure the topology file is a .yml/.yaml file under the allowed Containerlab directories.",
            )

        return (
            "BAD_REQUEST",
            "Request could not be processed.",
            "Check the request body, path parameters, and query parameters.",
        )

    if status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
        return (
            "METHOD_NOT_ALLOWED",
            "This HTTP method is not allowed for the requested endpoint.",
            "Check whether the endpoint expects GET, POST, PUT, or DELETE.",
        )

    return (
        f"HTTP_{status_code}_ERROR",
        "Request failed.",
        "Check the request details and try again.",
    )


def _classify_validation_error(
    errors: list[dict[str, Any]],
) -> tuple[str, str, str]:
    for error in errors:
        location = error.get("loc", [])
        error_type = error.get("type", "")

        if "difficulty" in location and error_type == "enum":
            return (
                "INVALID_DIFFICULTY",
                "Invalid difficulty value.",
                "Use one of the supported values: easy, medium, hard.",
            )

        if "body" in location and error_type in {"missing", "json_invalid"}:
            return (
                "INVALID_REQUEST_BODY",
                "Request body is missing or invalid.",
                "Send a valid JSON body with the required fields.",
            )

    return (
        "VALIDATION_ERROR",
        "Request validation failed.",
        "Check required fields, field types, and allowed enum values.",
    )