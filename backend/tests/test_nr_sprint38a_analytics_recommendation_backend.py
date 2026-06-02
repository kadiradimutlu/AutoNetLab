import json

from app.services.network_topics import (
    normalize_network_topic,
    topic_for_validation_check,
)
from app.services.recommendation.features import build_topic_performance
from app.services.recommendation.rule_based import build_rule_based_recommendations
from app.services.scenario_catalog import (
    CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID,
    SR_BASIC_LINK_SCENARIO_ID,
)
from app.services.validation_service import CAMPUS_CORE_STATIC_ROUTING_CHECKS


def test_nr_sprint38a_normalizes_legacy_and_campus_topics():
    assert normalize_network_topic("interface_status") == "interface_state"
    assert normalize_network_topic("connectivity") == "connectivity_testing"
    assert normalize_network_topic("routing") == "static_routing"
    assert normalize_network_topic("unknown") == "general_troubleshooting"

    campus_topics = {
        spec["check_id"]: topic_for_validation_check(spec["check_id"], spec.get("topic"))
        for spec in CAMPUS_CORE_STATIC_ROUTING_CHECKS
    }

    assert campus_topics["campus_check_1_client1_address"] == "ip_addressing"
    assert campus_topics["campus_check_2_client1_default_gateway"] == "default_gateway"
    assert campus_topics["campus_check_4_client2_default_gateway"] == "default_gateway"
    assert campus_topics["campus_check_5_client1_to_client2_connectivity"] == "connectivity_testing"
    assert campus_topics["campus_check_6_client2_to_client1_connectivity"] == "connectivity_testing"
    assert campus_topics["campus_check_7_srl1_edge_and_core_interfaces"] == "interface_state"
    assert campus_topics["campus_check_8_srl2_edge_and_core_interfaces"] == "interface_state"
    assert campus_topics["campus_check_9_srl3_transit_routes"] == "static_routing"


def test_nr_sprint38a_recommendations_are_topic_aware_and_student_safe():
    validation_result = {
        "score": 72,
        "passed": False,
        "checks": [
            {
                "check_id": "campus_check_4_client2_default_gateway",
                "topic": "default_gateway",
                "passed": False,
                "points": 0,
                "max_points": 10,
                "message": "Default Gateway validation failed on client2.",
                "evidence": {
                    "observed_output": "default via 10.10.20.254 dev eth1",
                    "command": "ip route",
                },
            },
            {
                "check_id": "campus_check_5_client1_to_client2_connectivity",
                "topic": "connectivity",
                "passed": False,
                "points": 0,
                "max_points": 10,
                "message": "Connectivity Testing validation failed on client1.",
                "evidence": {"observed_output": "packet loss"},
            },
            {
                "check_id": "campus_check_1_client1_address",
                "topic": "ip_addressing",
                "passed": True,
                "points": 10,
                "max_points": 10,
                "message": "IP Addressing validation passed on client1.",
            },
        ],
    }

    topic_performance = build_topic_performance(validation_result)
    recommendations = build_rule_based_recommendations(
        validation_result=validation_result,
        topic_performance=topic_performance,
    )

    topics = {item["topic"] for item in recommendations}
    assert "default_gateway" in topics
    assert "connectivity_testing" in topics

    serialized = json.dumps(recommendations)
    assert "Review the client default gateway configuration." in serialized
    assert "Test end-to-end connectivity after each correction." in serialized
    assert "default via 10.10.20.254" not in serialized
    assert "ip route replace" not in serialized
    assert "evidence" not in serialized
    assert "injected" not in serialized.lower()


def test_nr_sprint38a_pass_recommendation_is_positive_completion_guidance():
    validation_result = {
        "score": 100,
        "passed": True,
        "checks": [
            {
                "check_id": "campus_check_1_client1_address",
                "topic": "ip_addressing",
                "passed": True,
                "points": 10,
                "max_points": 10,
                "message": "IP Addressing validation passed on client1.",
            }
        ],
    }

    recommendations = build_rule_based_recommendations(
        validation_result=validation_result,
        topic_performance=build_topic_performance(validation_result),
    )

    assert recommendations[0]["topic"] == "lab_lifecycle"
    assert recommendations[0]["label"] == "Lab Completion"
    assert recommendations[0]["priority"] == "low"
    assert "successfully" in recommendations[0]["explanation"]


def test_nr_sprint38a_instructor_analytics_adds_scenario_difficulty_and_topic_views(monkeypatch):
    from app.services import instructor_analytics_service as service

    fake_sessions = [
        {
            "session_id": "lab-campus-fail",
            "student_id": "student-a",
            "difficulty": "easy",
            "status": "validated",
            "topology_template": CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID,
            "created_at": "2026-05-30T20:00:00+00:00",
            "completed_at": "2026-05-30T20:10:00+00:00",
            "score": 72,
            "passed": False,
            "validation_result": {
                "score": 72,
                "passed": False,
                "checks": [
                    {
                        "check_id": "campus_check_4_client2_default_gateway",
                        "topic": "default_gateway",
                        "passed": False,
                        "points": 0,
                        "max_points": 10,
                    },
                    {
                        "check_id": "campus_check_5_client1_to_client2_connectivity",
                        "topic": "connectivity",
                        "passed": False,
                        "points": 0,
                        "max_points": 10,
                    },
                ],
            },
        },
        {
            "session_id": "lab-campus-pass",
            "student_id": "student-a",
            "difficulty": "easy",
            "status": "finished",
            "topology_template": CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID,
            "created_at": "2026-05-30T20:20:00+00:00",
            "completed_at": "2026-05-30T20:30:00+00:00",
            "score": 100,
            "passed": True,
            "validation_result": {
                "score": 100,
                "passed": True,
                "checks": [
                    {
                        "check_id": "campus_check_4_client2_default_gateway",
                        "topic": "default_gateway",
                        "passed": True,
                        "points": 10,
                        "max_points": 10,
                    }
                ],
            },
        },
        {
            "session_id": "lab-srl-fail",
            "student_id": "student-a",
            "difficulty": "medium",
            "status": "validated",
            "topology_template": SR_BASIC_LINK_SCENARIO_ID,
            "created_at": "2026-05-30T20:40:00+00:00",
            "completed_at": "2026-05-30T20:50:00+00:00",
            "score": 80,
            "passed": False,
            "validation_result": {
                "score": 80,
                "passed": False,
                "checks": [
                    {
                        "check_id": "srl_check_4_client_default_gateway",
                        "topic": "default_gateway",
                        "passed": False,
                        "points": 0,
                        "max_points": 20,
                    }
                ],
            },
        },
        {
            "session_id": "lab-cleanup",
            "student_id": "student-b",
            "difficulty": "easy",
            "status": "error",
            "topology_template": CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID,
            "runtime_cleanup_history": [{"success": True}],
            "created_at": "2026-05-30T21:00:00+00:00",
            "completed_at": None,
        },
    ]

    monkeypatch.setattr(service, "_load_session_records", lambda: fake_sessions)

    summary = service.get_analytics_summary()
    assert summary["success"] is True
    assert summary["cleanup_error_incidents"] == 1
    assert any(
        item["scenario_id"] == CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID
        and item["total_sessions"] == 3
        for item in summary["scenario_performance"]
    )
    assert any(
        item["difficulty"] == "easy"
        and item["total_sessions"] == 3
        for item in summary["difficulty_performance"]
    )

    weaknesses = service.get_topic_weaknesses()["topic_weaknesses"]
    default_gateway = next(item for item in weaknesses if item["topic"] == "default_gateway")
    assert default_gateway["attempts"] == default_gateway["attempt_count"]
    assert default_gateway["failures"] == default_gateway["fail_count"]
    assert default_gateway["fail_count"] == 2
    assert default_gateway["average_score_impact"] > 0

    recent = service.get_recent_sessions(limit=1)["recent_sessions"][0]
    assert recent["scenario_id"] == CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID
    assert recent["topology_template"] == CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID

    student_summary = service.get_student_summary("student-a")
    assert student_summary["repeated_failed_topics"][0]["topic"] == "default_gateway"
