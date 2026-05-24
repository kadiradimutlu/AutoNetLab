
from typing import Any

from app.db.repositories import persist_recommendation_snapshot
from app.schemas.enums import SessionStatus
from app.services.recommendation.features import (
    build_ml_feature_rows,
    build_topic_performance,
)
from app.services.recommendation.ml_prototype import predict_topic_priorities
from app.services.recommendation.rule_based import build_rule_based_recommendations


def build_recommendations_for_session(session: dict[str, Any]) -> dict[str, Any]:
    validation_result = session.get("validation_result")

    if not isinstance(validation_result, dict):
        payload = {
            "success": True,
            "session_id": session["session_id"],
            "status": session.get("status", SessionStatus.created),
            "score": session.get("score"),
            "passed": session.get("passed"),
            "source": "rule_based",
            "fallback_used": True,
            "recommendations": [],
            "message": (
                "No validation result found yet. Run validation before requesting "
                "personalized learning recommendations."
            ),
        }

        persist_recommendation_snapshot(session, payload)
        return payload

    score = validation_result.get("score")
    passed = validation_result.get("passed")

    topic_performance = session.get("topic_performance")

    if not isinstance(topic_performance, list):
        topic_performance = build_topic_performance(validation_result)

    feature_rows = build_ml_feature_rows(
        topic_performance=topic_performance,
        overall_score=score,
    )

    ml_predictions_list = predict_topic_priorities(feature_rows)
    ml_predictions = {
        item["topic"]: item
        for item in ml_predictions_list
    } if ml_predictions_list else {}

    if ml_predictions:
        source = "hybrid"
        fallback_used = False
        message = (
            "Hybrid recommendations generated using rule-based validation signals "
            "and the optional ML prototype."
        )
    else:
        source = "rule_based"
        fallback_used = True
        message = (
            "Rule-based fallback recommendations generated successfully. "
            "ML prototype was unavailable or did not produce a reliable prediction."
        )

    recommendations = build_rule_based_recommendations(
        validation_result=validation_result,
        topic_performance=topic_performance,
        source=source,
        ml_predictions=ml_predictions,
    )

    payload = {
        "success": True,
        "session_id": session["session_id"],
        "status": session.get("status", SessionStatus.validated),
        "score": score,
        "passed": passed,
        "source": source,
        "fallback_used": fallback_used,
        "recommendations": recommendations,
        "message": message,
    }

    persist_recommendation_snapshot(session, payload)
    return payload
