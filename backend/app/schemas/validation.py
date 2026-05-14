from pydantic import BaseModel, Field

from app.schemas.enums import SessionStatus


class ValidationCheck(BaseModel):
    check_id: str = Field(..., examples=["check_1_vlan_mismatch"])
    topic: str = Field(..., examples=["VLAN"])
    passed: bool = Field(..., examples=[False])
    message: str = Field(..., examples=["VLAN issue still exists on r1."])


class ValidationResult(BaseModel):
    success: bool = True
    session_id: str
    status: SessionStatus
    passed: bool
    score: int = Field(..., ge=0, le=100)
    checks: list[ValidationCheck]
    recommendations: list[str]