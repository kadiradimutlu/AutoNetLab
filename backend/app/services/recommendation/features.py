from typing import Any

from app.services.network_topics import (
    network_topic_label,
    network_topic_next_actions,
    normalize_network_topic,
)


def normalize_topic(value: Any) -> str:
    return normalize_network_topic(value)


def topic_label(topic: str) -> str:
    return network_topic_label(topic)


def topic_next_actions(topic: str) -> list[str]:
    return network_topic_next_actions(topic)


def build_topic_performance(validation_result: dict[str, Any]) -> list[dict[str, Any]]:
    checks = validation_result.get("checks", [])

    topic_stats: dict[str, dict[str, Any]] = {}

    for check in checks:
        topic_key = normalize_topic(check.get("topic", "general_troubleshooting"))

        if topic_key not in topic_stats:
            topic_stats[topic_key] = {
                "topic": topic_key,
                "label": topic_label(topic_key),
                "attempt_count": 0,
                "passed_count": 0,
                "fail_count": 0,
                "score_impact": 0,
                "failed_checks": [],
            }

        topic_stats[topic_key]["attempt_count"] += 1

        points = _coerce_int(check.get("points"), default=0)
        max_points = _coerce_int(check.get("max_points"), default=0)

        if check.get("passed") is True:
            topic_stats[topic_key]["passed_count"] += 1
        else:
            topic_stats[topic_key]["fail_count"] += 1
            topic_stats[topic_key]["score_impact"] += max(max_points - points, 0)
            topic_stats[topic_key]["failed_checks"].append(
                {
                    "check_id": str(check.get("check_id", "unknown_check")),
                    "topic": topic_key,
                    "message": str(check.get("message", "Validation check failed.")),
                }
            )

    performance_items: list[dict[str, Any]] = []

    for stats in topic_stats.values():
        attempt_count = stats["attempt_count"]
        fail_count = stats["fail_count"]
        passed_count = stats["passed_count"]

        failure_rate = round((fail_count / attempt_count) * 100, 2) if attempt_count else 0.0
        topic_score = round((passed_count / attempt_count) * 100, 2) if attempt_count else 100.0

        performance_items.append(
            {
                "topic": stats["topic"],
                "label": stats["label"],
                "attempt_count": attempt_count,
                "attempts": attempt_count,
                "passed_count": passed_count,
                "fail_count": fail_count,
                "failures": fail_count,
                "failure_rate": failure_rate,
                "topic_score": topic_score,
                "score_impact": stats["score_impact"],
                "failed_checks": stats["failed_checks"],
            }
        )

    performance_items.sort(
        key=lambda item: (item["fail_count"], item["failure_rate"], item["score_impact"]),
        reverse=True,
    )

    return performance_items


def build_ml_feature_rows(
    topic_performance: list[dict[str, Any]],
    overall_score: int | None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for item in topic_performance:
        if item.get("fail_count", 0) <= 0:
            continue

        rows.append(
            {
                "topic": item["topic"],
                "failure_rate": float(item.get("failure_rate", 0.0)),
                "failed_count": int(item.get("fail_count", 0)),
                "attempt_count": int(item.get("attempt_count", 0)),
                "overall_score": int(overall_score if overall_score is not None else 0),
            }
        )

    return rows


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
