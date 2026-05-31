from pydantic import BaseModel, Field


class DifficultyDistributionItem(BaseModel):
    difficulty: str = Field(..., examples=["medium"])
    session_count: int = Field(..., ge=0, examples=[12])
    completed_count: int = Field(..., ge=0, examples=[8])
    pass_rate: float = Field(default=0.0, ge=0, le=100, examples=[75.0])
    average_score: float = Field(..., ge=0, le=100, examples=[72.5])


class TopicWeaknessItem(BaseModel):
    topic: str = Field(..., examples=["ip_addressing"])
    label: str = Field(..., examples=["IP Addressing"])
    fail_count: int = Field(..., ge=0, examples=[5])
    attempt_count: int = Field(..., ge=0, examples=[9])
    failures: int = Field(default=0, ge=0, examples=[5])
    attempts: int = Field(default=0, ge=0, examples=[9])
    failure_rate: float = Field(..., ge=0, le=100, examples=[55.56])
    average_score: float = Field(..., ge=0, le=100, examples=[64.25])
    average_score_impact: float = Field(default=0.0, ge=0, le=100, examples=[27.5])
    severity: str = Field(..., examples=["medium"])


class RecentSessionItem(BaseModel):
    session_id: str = Field(..., examples=["lab-abc12345"])
    student_id: str = Field(..., examples=["demo-student"])
    difficulty: str = Field(..., examples=["medium"])
    status: str = Field(..., examples=["validated"])
    score: int | None = Field(default=None, ge=0, le=100, examples=[75])
    passed: bool | None = Field(default=None, examples=[False])
    scenario_id: str | None = Field(default=None, examples=["campus-core-routing"])
    topology_template: str | None = Field(default=None, examples=["campus-core-routing"])
    created_at: str | None = Field(default=None)
    completed_at: str | None = Field(default=None)


class StudentListItem(BaseModel):
    student_id: str = Field(..., examples=["demo-student"])
    total_sessions: int = Field(..., ge=0, examples=[6])
    completed_sessions: int = Field(..., ge=0, examples=[4])
    active_sessions: int = Field(..., ge=0, examples=[2])
    average_score: float = Field(..., ge=0, le=100, examples=[72.5])
    pass_rate: float = Field(..., ge=0, le=100, examples=[50.0])
    repeated_failed_topics: list[TopicWeaknessItem] = Field(default_factory=list)
    last_activity_at: str | None = Field(default=None)


class ScoreTrendItem(BaseModel):
    session_id: str = Field(..., examples=["lab-abc12345"])
    difficulty: str = Field(..., examples=["medium"])
    status: str = Field(..., examples=["validated"])
    score: int | None = Field(default=None, ge=0, le=100, examples=[75])
    passed: bool | None = Field(default=None, examples=[False])
    scenario_id: str | None = Field(default=None, examples=["campus-core-routing"])
    topology_template: str | None = Field(default=None, examples=["campus-core-routing"])
    created_at: str | None = Field(default=None)
    completed_at: str | None = Field(default=None)


class ScenarioPerformanceItem(BaseModel):
    scenario_id: str = Field(..., examples=["campus-core-routing"])
    total_sessions: int = Field(..., ge=0, examples=[10])
    completed_sessions: int = Field(..., ge=0, examples=[8])
    passed_sessions: int = Field(default=0, ge=0, examples=[6])
    pass_rate: float = Field(..., ge=0, le=100, examples=[75.0])
    average_score: float = Field(..., ge=0, le=100, examples=[82.5])


class DifficultyPerformanceItem(BaseModel):
    difficulty: str = Field(..., examples=["easy"])
    total_sessions: int = Field(..., ge=0, examples=[10])
    completed_sessions: int = Field(..., ge=0, examples=[8])
    passed_sessions: int = Field(default=0, ge=0, examples=[6])
    pass_rate: float = Field(..., ge=0, le=100, examples=[75.0])
    average_score: float = Field(..., ge=0, le=100, examples=[82.5])


class AnalyticsSummaryResponse(BaseModel):
    success: bool = True
    total_sessions: int = Field(..., ge=0)
    completed_sessions: int = Field(..., ge=0)
    active_sessions: int = Field(..., ge=0)
    passed_sessions: int = Field(..., ge=0)
    average_score: float = Field(..., ge=0, le=100)
    pass_rate: float = Field(..., ge=0, le=100)
    scenario_performance: list[ScenarioPerformanceItem] = Field(default_factory=list)
    difficulty_performance: list[DifficultyPerformanceItem] = Field(default_factory=list)
    topic_weaknesses: list[TopicWeaknessItem] = Field(default_factory=list)
    cleanup_error_incidents: int = Field(default=0, ge=0)
    message: str


class DifficultyDistributionResponse(BaseModel):
    success: bool = True
    distribution: list[DifficultyDistributionItem]
    difficulty_performance: list[DifficultyPerformanceItem] = Field(default_factory=list)
    message: str


class TopicWeaknessResponse(BaseModel):
    success: bool = True
    topic_weaknesses: list[TopicWeaknessItem]
    message: str


class RecentSessionsResponse(BaseModel):
    success: bool = True
    recent_sessions: list[RecentSessionItem]
    message: str


class StudentListResponse(BaseModel):
    success: bool = True
    students: list[StudentListItem]
    message: str


class StudentSummaryResponse(BaseModel):
    success: bool = True
    student_id: str
    total_sessions: int = Field(..., ge=0)
    completed_sessions: int = Field(..., ge=0)
    active_sessions: int = Field(..., ge=0)
    passed_sessions: int = Field(..., ge=0)
    average_score: float = Field(..., ge=0, le=100)
    pass_rate: float = Field(..., ge=0, le=100)
    repeated_failed_topics: list[TopicWeaknessItem] = Field(default_factory=list)
    first_seen_at: str | None = Field(default=None)
    last_activity_at: str | None = Field(default=None)
    message: str


class StudentSessionsResponse(BaseModel):
    success: bool = True
    student_id: str
    sessions: list[RecentSessionItem]
    message: str


class StudentTopicWeaknessResponse(BaseModel):
    success: bool = True
    student_id: str
    topic_weaknesses: list[TopicWeaknessItem]
    message: str


class StudentScoreTrendResponse(BaseModel):
    success: bool = True
    student_id: str
    score_trend: list[ScoreTrendItem]
    message: str
