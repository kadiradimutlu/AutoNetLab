from pydantic import BaseModel, Field

from app.schemas.enums import SessionStatus


class ValidationCheck(BaseModel):
    check_id: str = Field(..., examples=["check_vlan_r1"])
    topic: str = Field(..., examples=["VLAN"])
    passed: bool = Field(..., examples=[True])
    message: str = Field(..., examples=["VLAN configuration is correct."])


class ValidationResult(BaseModel):
    session_id: str
    status: SessionStatus
    passed: bool
    score: int = Field(..., ge=0, le=100, examples=[75])
    checks: list[ValidationCheck]
    recommendations: list[str]