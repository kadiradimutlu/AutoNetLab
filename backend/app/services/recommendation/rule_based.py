from typing import Any

from app.services.recommendation.features import (
    topic_label,
    topic_next_actions,
)


def build_rule_based_recommendations(
    validation_result: dict[str, Any],
    topic_performance: list[dict[str, Any]],
    source: str = "rule_based",
    ml_predictions: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    score = validation_result.get("score")
    passed = validation_result.get("passed")

    failed_topics = [
        item
        for item in topic_performance
        if item.get("fail_count", 0) > 0
    ]

    if not failed_topics:
        return [
            {
                "topic": "next_challenge",
                "label": "Next Challenge",
                "reason": "No failed validation checks were detected.",
                "explanation": (
                    "The current lab appears to be completed successfully. "
                    "The student can continue with a higher difficulty level or repeat the lab for practice."
                ),
                "priority": "low",
                "confidence": 0.75,
                "source": "rule_based",
                "next_actions": [
                    "Try a higher difficulty lab.",
                    "Repeat the same lab and solve it faster.",
                    "Review the validation result to understand why all checks passed.",
                ],
                "related_failed_checks": [],
            }
        ]

    recommendations: list[dict[str, Any]] = []

    for item in failed_topics:
        topic = item["topic"]
        label = item.get("label") or topic_label(topic)
        failure_rate = float(item.get("failure_rate", 0.0))
        fail_count = int(item.get("fail_count", 0))

        rule_priority = _priority_from_rule(
            failure_rate=failure_rate,
            fail_count=fail_count,
            score=score,
        )
        rule_confidence = _confidence_from_rule(rule_priority)

        ml_prediction = (ml_predictions or {}).get(topic)

        if ml_prediction:
            priority = ml_prediction.get("priority", rule_priority)
            confidence = max(rule_confidence, float(ml_prediction.get("confidence", 0.0)))
            item_source = source
            reason = f"Rule-based validation and ML prototype both indicate weakness in {label}."
        else:
            priority = rule_priority
            confidence = rule_confidence
            item_source = "rule_based"
            reason = f"Failed validation checks indicate weakness in {label}."

        recommendations.append(
            {
                "topic": topic,
                "label": label,
                "reason": reason,
                "explanation": _build_explanation(
                    label=label,
                    failure_rate=failure_rate,
                    fail_count=fail_count,
                    score=score,
                    passed=passed,
                ),
                "priority": priority,
                "confidence": round(min(confidence, 0.98), 2),
                "source": item_source,
                "next_actions": topic_next_actions(topic),
                "related_failed_checks": item.get("failed_checks", []),
            }
        )

    recommendations.sort(
        key=lambda item: _priority_sort_value(item["priority"]),
        reverse=True,
    )

    return recommendations


def _priority_from_rule(
    failure_rate: float,
    fail_count: int,
    score: int | None,
) -> str:
    if failure_rate >= 60 or fail_count >= 3 or (score is not None and score < 50):
        return "high"

    if failure_rate >= 30 or fail_count >= 1 or (score is not None and score < 80):
        return "medium"

    return "low"


def _confidence_from_rule(priority: str) -> float:
    if priority == "high":
        return 0.9

    if priority == "medium":
        return 0.78

    return 0.65


def _priority_sort_value(priority: str) -> int:
    return {
        "low": 1,
        "medium": 2,
        "high": 3,
    }.get(priority, 0)


def _build_explanation(
    label: str,
    failure_rate: float,
    fail_count: int,
    score: int | None,
    passed: bool | None,
) -> str:
    score_text = "unknown" if score is None else str(score)

    if passed is True:
        return (
            f"{label} is not currently blocking the lab result, but it can still be reviewed "
            f"as part of improvement practice. Current score: {score_text}."
        )

    return (
        f"{fail_count} validation check(s) related to {label} failed. "
        f"The topic failure rate is {failure_rate}%. Current score: {score_text}. "
        "The student should focus on this topic before attempting a harder lab."
    )
