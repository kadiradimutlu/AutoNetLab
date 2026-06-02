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
    validation_result: dict[str, Any] | None = None,
    session: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    validation_result = validation_result if isinstance(validation_result, dict) else {}
    session = session if isinstance(session, dict) else {}

    scenario_id = _scenario_id_from_session(session) or str(validation_result.get("scenario_id") or "")
    difficulty = str(session.get("difficulty") or validation_result.get("difficulty") or "")

    fault_resolution_score = _coerce_int(
        validation_result.get("fault_resolution_score"),
        default=_coerce_int(overall_score, default=0),
    )
    network_health_score = _coerce_int(
        validation_result.get("network_health_score"),
        default=fault_resolution_score,
    )

    affected_topics = _list_of_strings(validation_result.get("affected_topics"))
    failed_topics = _list_of_strings(validation_result.get("failed_topics"))
    resolved_topics = _list_of_strings(validation_result.get("resolved_topics"))

    ml_training_sample = validation_result.get("ml_training_sample")
    if isinstance(ml_training_sample, dict):
        affected_topics.extend(_list_of_strings(ml_training_sample.get("affected_topics")))
        failed_topics.extend(_list_of_strings(ml_training_sample.get("failed_topics")))
        resolved_topics.extend(_list_of_strings(ml_training_sample.get("resolved_topics")))

    rows: list[dict[str, Any]] = []

    for item in topic_performance:
        if item.get("fail_count", 0) <= 0:
            continue

        topic = str(item.get("topic") or "general_troubleshooting")
        failed_checks = item.get("failed_checks", [])
        failed_check_ids: list[str] = []

        if isinstance(failed_checks, list):
            for failed_check in failed_checks:
                if not isinstance(failed_check, dict):
                    continue

                check_id = failed_check.get("check_id")
                if check_id:
                    failed_check_ids.append(str(check_id))

        row_failed_topics = sorted(set([topic, *failed_topics]))

        rows.append(
            {
                "topic": topic,
                "scenario_id": scenario_id,
                "difficulty": difficulty,
                "failure_rate": float(item.get("failure_rate", 0.0)),
                "failed_count": int(item.get("fail_count", 0)),
                "attempt_count": int(item.get("attempt_count", 0)),
                "overall_score": int(overall_score if overall_score is not None else 0),
                "score_impact": int(item.get("score_impact", 0)),
                "failed_check_ids": failed_check_ids,
                "failed_topics": row_failed_topics,
                "affected_topics": sorted(set(affected_topics)),
                "resolved_topics": sorted(set(resolved_topics)),
                "fault_resolution_score": fault_resolution_score,
                "network_health_score": network_health_score,
                "passed": validation_result.get("passed"),
            }
        )

    return rows


def _scenario_id_from_session(session: dict[str, Any]) -> str:
    scenario = session.get("scenario")

    if isinstance(scenario, dict) and scenario.get("id"):
        return str(scenario["id"])

    if session.get("scenario_id"):
        return str(session["scenario_id"])

    if session.get("topology_template"):
        return str(session["topology_template"])

    return ""


def _list_of_strings(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, (list, tuple, set)):
        return [
            str(item)
            for item in value
            if item is not None and str(item).strip()
        ]

    if isinstance(value, str) and value.strip():
        return [value]

    return []


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default



def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
