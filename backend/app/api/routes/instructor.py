from fastapi import APIRouter, Depends, Query

from app.core.auth import require_instructor
from app.schemas.auth import AuthenticatedUser
from app.schemas.instructor import (
    AnalyticsSummaryResponse,
    DifficultyDistributionResponse,
    RecentSessionsResponse,
    StudentListResponse,
    StudentScoreTrendResponse,
    StudentSessionsResponse,
    StudentSummaryResponse,
    StudentTopicWeaknessResponse,
    TopicWeaknessResponse,
)
from app.services.instructor_analytics_service import (
    get_analytics_summary,
    get_difficulty_distribution,
    get_recent_sessions,
    get_student_score_trend,
    get_student_sessions,
    get_student_summary,
    get_student_topic_weaknesses,
    get_students,
    get_topic_weaknesses,
)

router = APIRouter(prefix="/instructor", tags=["Instructor Analytics"])


@router.get(
    "/analytics/summary",
    response_model=AnalyticsSummaryResponse,
)
def instructor_analytics_summary(
    _current_user: AuthenticatedUser = Depends(require_instructor),
) -> AnalyticsSummaryResponse:
    return AnalyticsSummaryResponse(**get_analytics_summary())


@router.get(
    "/analytics/difficulty-distribution",
    response_model=DifficultyDistributionResponse,
)
def instructor_difficulty_distribution(
    _current_user: AuthenticatedUser = Depends(require_instructor),
) -> DifficultyDistributionResponse:
    return DifficultyDistributionResponse(**get_difficulty_distribution())


@router.get(
    "/analytics/topic-weaknesses",
    response_model=TopicWeaknessResponse,
)
def instructor_topic_weaknesses(
    _current_user: AuthenticatedUser = Depends(require_instructor),
) -> TopicWeaknessResponse:
    return TopicWeaknessResponse(**get_topic_weaknesses())


@router.get(
    "/sessions/recent",
    response_model=RecentSessionsResponse,
)
def instructor_recent_sessions(
    limit: int = Query(default=10, ge=1, le=50),
    _current_user: AuthenticatedUser = Depends(require_instructor),
) -> RecentSessionsResponse:
    return RecentSessionsResponse(**get_recent_sessions(limit=limit))


@router.get(
    "/students",
    response_model=StudentListResponse,
)
def instructor_students(
    limit: int = Query(default=100, ge=1, le=500),
    _current_user: AuthenticatedUser = Depends(require_instructor),
) -> StudentListResponse:
    return StudentListResponse(**get_students(limit=limit))


@router.get(
    "/students/{student_id}/summary",
    response_model=StudentSummaryResponse,
)
def instructor_student_summary(
    student_id: str,
    _current_user: AuthenticatedUser = Depends(require_instructor),
) -> StudentSummaryResponse:
    return StudentSummaryResponse(**get_student_summary(student_id=student_id))


@router.get(
    "/students/{student_id}/sessions",
    response_model=StudentSessionsResponse,
)
def instructor_student_sessions(
    student_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    _current_user: AuthenticatedUser = Depends(require_instructor),
) -> StudentSessionsResponse:
    return StudentSessionsResponse(
        **get_student_sessions(
            student_id=student_id,
            limit=limit,
        )
    )


@router.get(
    "/students/{student_id}/topic-weaknesses",
    response_model=StudentTopicWeaknessResponse,
)
def instructor_student_topic_weaknesses(
    student_id: str,
    _current_user: AuthenticatedUser = Depends(require_instructor),
) -> StudentTopicWeaknessResponse:
    return StudentTopicWeaknessResponse(
        **get_student_topic_weaknesses(student_id=student_id)
    )


@router.get(
    "/students/{student_id}/score-trend",
    response_model=StudentScoreTrendResponse,
)
def instructor_student_score_trend(
    student_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    _current_user: AuthenticatedUser = Depends(require_instructor),
) -> StudentScoreTrendResponse:
    return StudentScoreTrendResponse(
        **get_student_score_trend(
            student_id=student_id,
            limit=limit,
        )
    )
