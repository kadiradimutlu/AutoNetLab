import re
from typing import Any


TOPIC_LABELS = {
    "ip_addressing": "IP Addressing",
    "subnetting": "Subnetting",
    "interface_status": "Interface Status",
    "routing": "Routing",
    "default_gateway": "Default Gateway",
    "vlan": "VLAN",
    "acl": "ACL",
    "connectivity": "Connectivity",
    "trunk_configuration": "Trunk Configuration",
    "unknown": "Unknown",
}


TOPIC_NEXT_ACTIONS = {
    "ip_addressing": [
        "Review IP address and subnet mask configuration.",
        "Compare both router interfaces that are connected to the same link.",
        "Run basic connectivity tests after fixing addressing issues.",
    ],
    "subnetting": [
        "Review subnet boundaries and valid host ranges.",
        "Check whether both endpoints are in compatible subnets.",
    ],
    "interface_status": [
        "Check whether the required interfaces are enabled.",
        "Verify interface names and link status before testing connectivity.",
    ],
    "routing": [
        "Review static route or default route configuration.",
        "Check next-hop addresses and reachable networks.",
    ],
    "default_gateway": [
        "Verify the configured default gateway.",
        "Check whether the gateway address belongs to the correct subnet.",
    ],
    "vlan": [
        "Review VLAN IDs on access ports.",
        "Check whether both sides use consistent VLAN configuration.",
    ],
    "acl": [
        "Review ACL rules and their direction.",
        "Check whether traffic is blocked by an unintended deny rule.",
    ],
    "connectivity": [
        "Start with ping tests between directly connected devices.",
        "Work layer by layer: interface, addressing, routing, then policy rules.",
    ],
    "trunk_configuration": [
        "Review allowed VLANs on trunk links.",
        "Check whether the same VLAN is permitted on both sides of the trunk.",
    ],
    "unknown": [
        "Review the failed validation message carefully.",
        "Repeat the troubleshooting process step by step.",
    ],
}


def normalize_topic(value: Any) -> str:
    if value is None:
        return "unknown"

    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = text.strip("_")

    return text or "unknown"


def topic_label(topic: str) -> str:
    topic_key = normalize_topic(topic)
    return TOPIC_LABELS.get(topic_key, str(topic).replace("_", " ").title())


def topic_next_actions(topic: str) -> list[str]:
    topic_key = normalize_topic(topic)
    return TOPIC_NEXT_ACTIONS.get(topic_key, TOPIC_NEXT_ACTIONS["unknown"])


def build_topic_performance(validation_result: dict[str, Any]) -> list[dict[str, Any]]:
    checks = validation_result.get("checks", [])

    topic_stats: dict[str, dict[str, Any]] = {}

    for check in checks:
        topic_key = normalize_topic(check.get("topic", "unknown"))

        if topic_key not in topic_stats:
            topic_stats[topic_key] = {
                "topic": topic_key,
                "label": topic_label(topic_key),
                "attempt_count": 0,
                "passed_count": 0,
                "fail_count": 0,
                "failed_checks": [],
            }

        topic_stats[topic_key]["attempt_count"] += 1

        if check.get("passed") is True:
            topic_stats[topic_key]["passed_count"] += 1
        else:
            topic_stats[topic_key]["fail_count"] += 1
            topic_stats[topic_key]["failed_checks"].append(
                {
                    "check_id": check.get("check_id", "unknown_check"),
                    "topic": check.get("topic", topic_label(topic_key)),
                    "message": check.get("message", "Validation check failed."),
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
                "passed_count": passed_count,
                "fail_count": fail_count,
                "failure_rate": failure_rate,
                "topic_score": topic_score,
                "failed_checks": stats["failed_checks"],
            }
        )

    performance_items.sort(
        key=lambda item: (item["fail_count"], item["failure_rate"]),
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
