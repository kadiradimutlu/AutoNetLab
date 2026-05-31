from app.schemas.enums import Difficulty, SessionStatus
from app.schemas.validation import ValidationCheck
from app.services.scenario_catalog import CAMPUS_CORE_ROUTING_SCENARIO_ID
from app.services.session_service import _build_validation_attempt_payload
from app.services.validation_service import (
    _build_scored_validation_result,
    validate_session,
)


def _session(injected_errors=None):
    return {
        "session_id": "lab-cp4-score",
        "student_id": "student",
        "difficulty": Difficulty.hard,
        "status": SessionStatus.deployed,
        "scenario": {"id": CAMPUS_CORE_ROUTING_SCENARIO_ID},
        "topology_template": CAMPUS_CORE_ROUTING_SCENARIO_ID,
        "injected_errors": injected_errors or [],
        "validation_attempts": [],
    }


def _check(check_id, topic, device, passed, expected_state):
    return ValidationCheck(
        check_id=check_id,
        topic=topic,
        description=f"{topic} check on {device}",
        status="passed" if passed else "failed",
        passed=passed,
        points=10 if passed else 0,
        max_points=10,
        message="ok" if passed else "failed",
        hint="general hint",
        evidence={
            "validation_mode": "srlinux_live_state_check",
            "device": device,
            "expected_state": expected_state,
            "missing_expected_outputs": [] if passed else [expected_state],
        },
    )


def test_checkpoint4_score_is_fault_resolution_and_network_health_is_secondary():
    session = _session(
        injected_errors=[
            {
                "variant_id": "campus_client2_wrong_gateway",
                "topic": "default_gateway",
                "device": "client2",
                "expected_outputs": ["default via 10.10.20.1"],
            }
        ]
    )
    checks = [
        _check(
            "campus_check_4_client2_default_gateway",
            "default_gateway",
            "client2",
            True,
            "default via 10.10.20.1",
        ),
        _check(
            "campus_check_5_client1_to_client2_connectivity",
            "connectivity_testing",
            "client1",
            False,
            "bytes from 10.10.20.10",
        ),
    ]

    result = _build_scored_validation_result(
        session=session,
        checks=checks,
        recommendations=["Review connectivity."],
    )

    assert result.score_type == "fault_resolution"
    assert result.score == 100
    assert result.fault_resolution_score == 100
    assert result.network_health_score == 50
    assert result.passed is True
    assert result.affected_topics == ["default_gateway"]
    assert result.failed_topics == ["connectivity_testing"]
    assert result.resolved_topics == ["default_gateway"]
    assert result.ml_training_sample["scenario_id"] == CAMPUS_CORE_ROUTING_SCENARIO_ID
    assert result.ml_training_sample["difficulty"] == "hard"
    assert result.ml_training_sample["score_type"] == "fault_resolution"


def test_checkpoint4_unresolved_fault_lowers_primary_score():
    session = _session(
        injected_errors=[
            {
                "variant_id": "campus_client2_wrong_gateway",
                "topic": "default_gateway",
                "device": "client2",
                "expected_outputs": ["default via 10.10.20.1"],
            },
            {
                "variant_id": "campus_srl1_missing_route_to_client2",
                "topic": "static_routing",
                "device": "srl1",
                "expected_outputs": ["campus-srl1-to-client2"],
            },
        ]
    )
    checks = [
        _check(
            "campus_check_4_client2_default_gateway",
            "default_gateway",
            "client2",
            True,
            "default via 10.10.20.1",
        ),
        _check(
            "campus_check_10_srl1_route_to_client2",
            "static_routing",
            "srl1",
            False,
            "campus-srl1-to-client2",
        ),
    ]

    result = _build_scored_validation_result(
        session=session,
        checks=checks,
        recommendations=["Review static routing."],
    )

    assert result.score == 50
    assert result.fault_resolution_score == 50
    assert result.network_health_score == 50
    assert result.passed is False
    assert result.affected_topics == ["default_gateway", "static_routing"]
    assert result.failed_topics == ["static_routing"]
    assert result.resolved_topics == ["default_gateway"]


def test_checkpoint4_validation_attempt_history_preserves_both_score_types():
    session = _session()
    result_payload = {
        "session_id": "lab-cp4-score",
        "status": "validated",
        "passed": False,
        "score": 50,
        "score_type": "fault_resolution",
        "fault_resolution_score": 50,
        "network_health_score": 72,
        "affected_topics": ["default_gateway", "static_routing"],
        "failed_topics": ["static_routing"],
        "resolved_topics": ["default_gateway"],
        "ml_training_sample": {
            "scenario_id": CAMPUS_CORE_ROUTING_SCENARIO_ID,
            "difficulty": "hard",
            "score_type": "fault_resolution",
        },
        "checks": [
            {
                "check_id": "check_1",
                "topic": "static_routing",
                "description": "check",
                "status": "failed",
                "passed": False,
                "points": 0,
                "max_points": 10,
                "message": "failed",
                "hint": "hint",
                "evidence": {"hidden": "internal"},
            }
        ],
    }

    attempt = _build_validation_attempt_payload(
        session=session,
        result_payload=result_payload,
    )

    assert attempt["score"] == 50
    assert attempt["score_type"] == "fault_resolution"
    assert attempt["fault_resolution_score"] == 50
    assert attempt["network_health_score"] == 72
    assert attempt["affected_topics"] == ["default_gateway", "static_routing"]
    assert attempt["failed_topics"] == ["static_routing"]
    assert attempt["resolved_topics"] == ["default_gateway"]
    assert attempt["ml_training_sample"]["attempt_number"] == 1
    assert "evidence" not in attempt["checks"][0]


def test_checkpoint4_live_validation_result_exposes_score_type_metadata(monkeypatch):
    session = _session(
        injected_errors=[
            {
                "variant_id": "campus_client2_wrong_gateway",
                "topic": "default_gateway",
                "device": "client2",
                "expected_outputs": ["default via 10.10.20.1"],
            }
        ]
    )
    session["cli_access"] = [
        {"device_id": "client1", "name": "client1", "container_name": "client1"},
        {"device_id": "client2", "name": "client2", "container_name": "client2"},
        {"device_id": "srl1", "name": "srl1", "container_name": "srl1"},
        {"device_id": "srl2", "name": "srl2", "container_name": "srl2"},
        {"device_id": "srl3", "name": "srl3", "container_name": "srl3"},
    ]

    def fake_run_device_command(*, container_name, command, timeout):
        command_text = " ".join(str(part) for part in command)

        if container_name == "client2" and "ip route" in command_text:
            return {
                "return_code": 0,
                "output": "default via 10.10.20.254 dev eth1",
            }

        return {
            "return_code": 0,
            "output": (
                "10.10.10.10/24\n10.10.20.10/24\n"
                "default via 10.10.10.1\n"
                "bytes from 10.10.20.10\nbytes from 10.10.10.10\n"
                "10.10.10.1/24\n10.10.20.1/24\n"
                "campus-srl1-to-client2\ncampus-srl2-to-client1\n"
                "campus-srl3-to-client1\ncampus-srl3-to-client2"
            ),
        }

    monkeypatch.setattr(
        "app.services.validation_service._run_device_command",
        fake_run_device_command,
    )

    result = validate_session(session)

    assert result.score_type == "fault_resolution"
    assert result.score == 0
    assert result.fault_resolution_score == 0
    assert result.network_health_score < 100
    assert result.passed is False
    assert result.affected_topics == ["default_gateway"]
    assert "default_gateway" in result.failed_topics
