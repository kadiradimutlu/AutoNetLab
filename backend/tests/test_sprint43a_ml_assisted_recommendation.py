import json

from app.services.recommendation import engine as recommendation_engine
from app.services.recommendation.features import (
    build_ml_feature_rows,
    build_topic_performance,
)
from app.services.recommendation.ml_prototype import (
    get_ml_status,
    predict_topic_priorities,
)


def _validation_result_for_default_gateway_failure() -> dict:
    return {
        "score": 80,
        "passed": False,
        "fault_resolution_score": 80,
        "network_health_score": 80,
        "affected_topics": ["default_gateway", "connectivity_testing"],
        "failed_topics": ["default_gateway"],
        "resolved_topics": ["ip_addressing"],
        "checks": [
            {
                "check_id": "srl_check_4_client_default_gateway",
                "topic": "default_gateway",
                "passed": False,
                "points": 0,
                "max_points": 20,
                "message": "Default Gateway validation failed on client1.",
            },
            {
                "check_id": "srl_check_3_client_address",
                "topic": "ip_addressing",
                "passed": True,
                "points": 20,
                "max_points": 20,
                "message": "IP Addressing validation passed on client1.",
            },
        ],
    }


def _validation_result_for_static_routing_failure() -> dict:
    return {
        "score": 72,
        "passed": False,
        "fault_resolution_score": 72,
        "network_health_score": 72,
        "affected_topics": ["static_routing", "connectivity_testing"],
        "failed_topics": ["static_routing"],
        "resolved_topics": ["ip_addressing", "default_gateway"],
        "checks": [
            {
                "check_id": "campus_check_9_srl3_transit_routes",
                "topic": "static_routing",
                "passed": False,
                "points": 0,
                "max_points": 10,
                "message": "Static Routing validation failed on srl3.",
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


def test_sprint43a_ml_status_is_pure_python_and_available():
    status = get_ml_status()

    assert status["available"] is True
    assert status["library"] == "pure-python"
    assert status["error"] is None
    assert "scikit" not in json.dumps(status).lower()
    assert "sklearn" not in json.dumps(status).lower()


def test_sprint43a_classifier_returns_no_prediction_for_empty_features():
    assert predict_topic_priorities([]) is None


def test_sprint43a_classifier_predicts_default_gateway_topic():
    validation_result = _validation_result_for_default_gateway_failure()
    topic_performance = build_topic_performance(validation_result)
    rows = build_ml_feature_rows(
        topic_performance=topic_performance,
        overall_score=validation_result["score"],
        validation_result=validation_result,
        session={
            "scenario_id": "srl-edge-link",
            "topology_template": "srl-edge-link",
            "difficulty": "easy",
        },
    )

    predictions = predict_topic_priorities(rows)

    assert predictions
    prediction = next(item for item in predictions if item["topic"] == "default_gateway")
    assert prediction["priority"] in {"medium", "high"}
    assert prediction["confidence"] >= 0.42


def test_sprint43a_classifier_predicts_static_routing_topic():
    validation_result = _validation_result_for_static_routing_failure()
    topic_performance = build_topic_performance(validation_result)
    rows = build_ml_feature_rows(
        topic_performance=topic_performance,
        overall_score=validation_result["score"],
        validation_result=validation_result,
        session={
            "scenario_id": "campus-core-routing",
            "topology_template": "campus-core-routing",
            "difficulty": "hard",
        },
    )

    predictions = predict_topic_priorities(rows)

    assert predictions
    prediction = next(item for item in predictions if item["topic"] == "static_routing")
    assert prediction["priority"] == "high"
    assert prediction["confidence"] >= 0.42


def test_sprint43a_engine_uses_hybrid_output_without_breaking_payload_shape():
    validation_result = _validation_result_for_static_routing_failure()

    payload = recommendation_engine.build_recommendations_for_session(
        {
            "session_id": "lab-sprint43a-static",
            "status": "validated",
            "scenario_id": "campus-core-routing",
            "topology_template": "campus-core-routing",
            "difficulty": "hard",
            "score": validation_result["score"],
            "passed": False,
            "validation_result": validation_result,
        }
    )

    assert payload["success"] is True
    assert payload["source"] in {"hybrid", "rule_based"}
    assert isinstance(payload["fallback_used"], bool)
    assert payload["recommendations"]

    static_recommendation = next(
        item for item in payload["recommendations"] if item["topic"] == "static_routing"
    )

    assert static_recommendation["priority"] == "high"
    assert static_recommendation["confidence"] >= 0.8


def test_sprint43a_rule_based_fallback_survives_classifier_unavailable(monkeypatch):
    monkeypatch.setattr(
        recommendation_engine,
        "predict_topic_priorities",
        lambda feature_rows: None,
    )

    validation_result = _validation_result_for_default_gateway_failure()

    payload = recommendation_engine.build_recommendations_for_session(
        {
            "session_id": "lab-sprint43a-fallback",
            "status": "validated",
            "scenario_id": "srl-edge-link",
            "topology_template": "srl-edge-link",
            "difficulty": "easy",
            "score": validation_result["score"],
            "passed": False,
            "validation_result": validation_result,
        }
    )

    assert payload["success"] is True
    assert payload["source"] == "rule_based"
    assert payload["fallback_used"] is True
    assert payload["recommendations"]
    assert payload["recommendations"][0]["source"] == "rule_based"


def test_sprint43a_student_facing_text_does_not_expose_internal_labels():
    validation_result = _validation_result_for_default_gateway_failure()

    payload = recommendation_engine.build_recommendations_for_session(
        {
            "session_id": "lab-sprint43a-safe-text",
            "status": "validated",
            "scenario_id": "srl-edge-link",
            "topology_template": "srl-edge-link",
            "difficulty": "easy",
            "score": validation_result["score"],
            "passed": False,
            "validation_result": validation_result,
        }
    )

    student_facing_parts = [payload["message"]]

    for item in payload["recommendations"]:
        student_facing_parts.append(item["reason"])
        student_facing_parts.append(item["explanation"])
        student_facing_parts.extend(item.get("next_actions", []))

    student_facing_text = "\n".join(student_facing_parts).lower()

    forbidden_terms = [
        "ml_prototype",
        "ml prototype",
        "rule_based",
        "rule-based",
        "fallback",
        "source",
        "sklearn",
        "scikit",
        "debug",
        "evidence",
        "injected_errors",
        "validation_command",
        "injection_commands",
    ]

    for term in forbidden_terms:
        assert term not in student_facing_text
