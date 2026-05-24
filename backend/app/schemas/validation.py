from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.enums import SessionStatus


ValidationCheckStatus = Literal["passed", "failed", "warning", "skipped"]


class ValidationCheck(BaseModel):
    check_id: str = Field(..., examples=["check_1_ip_addressing"])
    topic: str = Field(..., examples=["ip_addressing"])
    description: str = Field(
        ...,
        examples=["Validate whether IP addressing related configuration state is correct."],
    )
    status: ValidationCheckStatus = Field(..., examples=["failed"])
    passed: bool = Field(..., examples=[False])
    points: int = Field(..., ge=0, examples=[0])
    max_points: int = Field(..., ge=0, examples=[20])
    message: str = Field(..., examples=["IP Addressing validation failed on r1."])
    hint: str | None = Field(
        default=None,
        examples=["Check IP address and subnet mask configuration."],
    )
    evidence: dict[str, Any] | None = Field(
        default=None,
        examples=[
            {
                "validation_mode": "config_marker_check",
                "device": "r1",
                "config_file_present": True,
                "observed_state": "issue marker is still present",
            }
        ],
    )


class ValidationResult(BaseModel):
    success: bool = True
    session_id: str
    status: SessionStatus
    passed: bool
    score: int = Field(..., ge=0, le=100)
    checks: list[ValidationCheck]
    recommendations: list[str]

class StudentValidationCheck(BaseModel):
    """
    Student-facing validation check.

    Evidence is intentionally excluded from this schema because it may expose
    internal validation state that belongs to instructor/debug views.
    """

    check_id: str = Field(..., examples=["check_1_ip_addressing"])
    topic: str = Field(..., examples=["ip_addressing"])
    description: str = Field(
        ...,
        examples=["Validate whether IP addressing related configuration state is correct."],
    )
    status: ValidationCheckStatus = Field(..., examples=["failed"])
    passed: bool = Field(..., examples=[False])
    points: int = Field(..., ge=0, examples=[0])
    max_points: int = Field(..., ge=0, examples=[20])
    message: str = Field(..., examples=["IP Addressing validation failed on r1."])
    hint: str | None = Field(
        default=None,
        examples=["Check IP address and subnet mask configuration."],
    )


class StudentValidationResult(BaseModel):
    """
    Student-facing validation result.

    Internal ValidationResult may still keep evidence for persistence,
    recommendations, analytics, and future instructor/debug views.
    """

    success: bool = True
    session_id: str
    status: SessionStatus
    passed: bool
    score: int = Field(..., ge=0, le=100)
    checks: list[StudentValidationCheck]
    recommendations: list[str]
