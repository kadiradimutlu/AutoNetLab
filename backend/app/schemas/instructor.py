from pydantic import BaseModel, Field


class DifficultyDistributionItem(BaseModel):
    difficulty: str = Field(..., examples=["medium"])
    session_count: int = Field(..., ge=0, examples=[12])
    completed_count: int = Field(..., ge=0, examples=[8])
    average_score: float = Field(..., ge=0, le=100, examples=[72.5])


class TopicWeaknessItem(BaseModel):
    topic: str = Field(..., examples=["ip_addressing"])
    label: str = Field(..., examples=["IP Addressing"])
    fail_count: int = Field(..., ge=0, examples=[5])
    attempt_count: int = Field(..., ge=0, examples=[9])
    failure_rate: float = Field(..., ge=0, le=100, examples=[55.56])
    average_score: float = Field(..., ge=0, le=100, examples=[64.25])
    severity: str = Field(..., examples=["medium"])


class RecentSessionItem(BaseModel):
    session_id: str = Field(..., examples=["lab-abc12345"])
    student_id: str = Field(..., examples=["demo-student"])
    difficulty: str = Field(..., examples=["medium"])
    status: str = Field(..., examples=["validated"])
    score: int | None = Field(default=None, ge=0, le=100, examples=[75])
    passed: bool | None = Field(default=None, examples=[False])
    created_at: str | None = Field(default=None)
    completed_at: str | None = Field(default=None)


class AnalyticsSummaryResponse(BaseModel):
    success: bool = True
    total_sessions: int = Field(..., ge=0)
    completed_sessions: int = Field(..., ge=0)
    active_sessions: int = Field(..., ge=0)
    passed_sessions: int = Field(..., ge=0)
    average_score: float = Field(..., ge=0, le=100)
    pass_rate: float = Field(..., ge=0, le=100)
    message: str


class DifficultyDistributionResponse(BaseModel):
    success: bool = True
    distribution: list[DifficultyDistributionItem]
    message: str


class TopicWeaknessResponse(BaseModel):
    success: bool = True
    topic_weaknesses: list[TopicWeaknessItem]
    message: str


class RecentSessionsResponse(BaseModel):
    success: bool = True
    recent_sessions: list[RecentSessionItem]
    message: str
