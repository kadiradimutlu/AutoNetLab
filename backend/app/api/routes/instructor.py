from fastapi import APIRouter, Query

from app.schemas.instructor import (
    AnalyticsSummaryResponse,
    DifficultyDistributionResponse,
    RecentSessionsResponse,
    TopicWeaknessResponse,
)
from app.services.instructor_analytics_service import (
    get_analytics_summary,
    get_difficulty_distribution,
    get_recent_sessions,
    get_topic_weaknesses,
)

router = APIRouter(prefix="/instructor", tags=["Instructor Analytics"])


@router.get(
    "/analytics/summary",
    response_model=AnalyticsSummaryResponse,
)
def instructor_analytics_summary() -> AnalyticsSummaryResponse:
    return AnalyticsSummaryResponse(**get_analytics_summary())


@router.get(
    "/analytics/difficulty-distribution",
    response_model=DifficultyDistributionResponse,
)
def instructor_difficulty_distribution() -> DifficultyDistributionResponse:
    return DifficultyDistributionResponse(**get_difficulty_distribution())


@router.get(
    "/analytics/topic-weaknesses",
    response_model=TopicWeaknessResponse,
)
def instructor_topic_weaknesses() -> TopicWeaknessResponse:
    return TopicWeaknessResponse(**get_topic_weaknesses())


@router.get(
    "/sessions/recent",
    response_model=RecentSessionsResponse,
)
def instructor_recent_sessions(
    limit: int = Query(default=10, ge=1, le=50),
) -> RecentSessionsResponse:
    return RecentSessionsResponse(**get_recent_sessions(limit=limit))
