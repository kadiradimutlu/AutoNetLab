from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.enums import SessionStatus


RecommendationSource = Literal["rule_based", "ml_prototype", "hybrid"]
RecommendationPriority = Literal["low", "medium", "high"]


class RelatedFailedCheck(BaseModel):
    check_id: str = Field(..., examples=["check_1_ip_address_mismatch"])
    topic: str = Field(..., examples=["ip_addressing"])
    message: str = Field(..., examples=["IP Addressing issue still exists on r1."])


class RecommendationItem(BaseModel):
    topic: str = Field(..., examples=["ip_addressing"])
    label: str = Field(..., examples=["IP Addressing"])
    reason: str = Field(..., examples=["Failed validation checks indicate weakness in IP Addressing."])
    explanation: str = Field(..., examples=["The student should review addressing, subnet masks, and interface configuration."])
    priority: RecommendationPriority = Field(..., examples=["high"])
    confidence: float = Field(..., ge=0, le=1, examples=[0.85])
    source: RecommendationSource = Field(..., examples=["rule_based"])
    next_actions: list[str] = Field(
        default_factory=list,
        examples=[["Review IP addressing rules.", "Check subnet masks on both routers."]],
    )
    related_failed_checks: list[RelatedFailedCheck] = Field(default_factory=list)


class RecommendationResponse(BaseModel):
    success: bool = True
    session_id: str
    status: SessionStatus
    score: int | None = Field(default=None, ge=0, le=100)
    passed: bool | None = None
    scenario_id: str | None = Field(default=None, examples=["campus-core-routing"])
    topology_template: str | None = Field(default=None, examples=["campus-core-routing"])
    source: RecommendationSource
    fallback_used: bool
    topic_performance: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: list[RecommendationItem]
    message: str
