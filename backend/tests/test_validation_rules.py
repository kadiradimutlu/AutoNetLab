from app.schemas.enums import Difficulty
from app.services.error_injection import ERROR_POOL, generate_errors
from app.services.validation_rules import (
    ERROR_VALIDATION_RULES,
    get_live_validation_rule,
)
from app.services.validation_service import _evaluate_live_container_state


def test_every_error_pool_item_has_runtime_and_validation_metadata():
    assert len(ERROR_POOL) >= 30

    for error in ERROR_POOL:
        assert error["code"]
        assert error["topic"]
        assert error["device"]
        assert error["variant_id"]
        assert error["injection_commands"]
        assert error["validation_command"]
        assert error["expected_outputs"]


def test_error_generation_is_deterministic_for_same_seed():
    first = generate_errors(
        difficulty=Difficulty.hard,
        seed="lab-deterministic",
        topology_devices=["r1", "r2", "r3", "r4"],
    )
    second = generate_errors(
        difficulty=Difficulty.hard,
        seed="lab-deterministic",
        topology_devices=["r1", "r2", "r3", "r4"],
    )

    assert [error.model_dump() for error in first] == [
        error.model_dump()
        for error in second
    ]


def test_error_generation_varies_across_many_seeds():
    observed_codes = set()
    observed_variants = set()

    for index in range(40):
        errors = generate_errors(
            difficulty=Difficulty.hard,
            seed=f"lab-variant-{index}",
            topology_devices=["r1", "r2", "r3", "r4"],
        )

        observed_codes.update(error.code for error in errors)
        observed_variants.update(error.variant_id for error in errors)

    assert len(observed_codes) >= 20
    assert len(observed_variants) >= 20


def test_generated_medium_errors_only_use_available_topology_devices():
    errors = generate_errors(
        difficulty=Difficulty.medium,
        seed="lab-medium",
        topology_devices=["r1", "r2", "r3"],
    )

    assert len(errors) == 3
    assert all(error.device in {"r1", "r2", "r3"} for error in errors)


def test_live_validation_prefers_session_specific_rule(monkeypatch):
    session = {
        "cli_access": [
            {
                "device_id": "r9",
                "name": "r9",
                "container_name": "clab-autonetlab-test-r9",
            }
        ]
    }

    error = {
        "code": "CUSTOM_SESSION_ERROR",
        "description": "Session-specific generated validation rule.",
        "validation_command": "show custom live state",
        "expected_outputs": ["custom-ok"],
    }

    def fake_run_container_command(container_name: str, command: str) -> str:
        assert container_name == "clab-autonetlab-test-r9"
        assert command == "show custom live state"
        return "custom-ok"

    monkeypatch.setattr(
        "app.services.validation_service._run_container_command",
        fake_run_container_command,
    )

    result = _evaluate_live_container_state(
        session=session,
        code="CUSTOM_SESSION_ERROR",
        topic="connectivity",
        device="r9",
        error=error,
    )

    assert result is not None
    assert result["passed"] is True
    assert result["evidence"]["validation_mode"] == "live_container_state_check"
    assert result["evidence"]["command"] == "show custom live state"
    assert result["evidence"]["expected_state"] == "custom-ok"


def test_live_validation_keeps_legacy_catalog_fallback(monkeypatch):
    session = {
        "cli_access": [
            {
                "device_id": "r1",
                "name": "r1",
                "container_name": "clab-autonetlab-test-r1",
            }
        ]
    }

    def fake_run_container_command(container_name: str, command: str) -> str:
        assert container_name == "clab-autonetlab-test-r1"
        assert command == "ip addr show eth1"
        return "2: eth1: <BROADCAST,UP,LOWER_UP> state UP\\n    inet 10.10.12.1/24 scope global eth1"

    monkeypatch.setattr(
        "app.services.validation_service._run_container_command",
        fake_run_container_command,
    )

    result = _evaluate_live_container_state(
        session=session,
        code="IP_ADDRESS_MISMATCH",
        topic="ip_addressing",
        device="r1",
    )

    assert result is not None
    assert result["passed"] is True
    assert result["evidence"]["command"] == "ip addr show eth1"
    assert get_live_validation_rule("IP_ADDRESS_MISMATCH") is not None
    assert "IP_ADDRESS_MISMATCH" in ERROR_VALIDATION_RULES


def test_acl_like_runtime_injection_uses_loopback_sink_route():
    acl_errors = [
        error
        for error in ERROR_POOL
        if error["topic"] == "acl_like"
    ]

    assert acl_errors

    for error in acl_errors:
        commands = " ".join(error["injection_commands"])
        assert " dev lo" in commands
        assert " via 10.10." not in commands


def test_live_validation_keeps_failed_ping_as_live_evidence(monkeypatch):
    session = {
        "cli_access": [
            {
                "device_id": "r3",
                "name": "r3",
                "container_name": "clab-autonetlab-test-r3",
            }
        ]
    }

    error = {
        "code": "CONNECTIVITY_FAILURE_R3_R4",
        "description": "Connectivity check should stay live even when ping fails.",
        "validation_command": "ping -c 1 -W 1 10.10.34.2",
        "expected_outputs": ["1 packets received"],
    }

    def fake_run_container_command(container_name: str, command: str) -> str:
        assert container_name == "clab-autonetlab-test-r3"
        assert command == "ping -c 1 -W 1 10.10.34.2"
        return "1 packets transmitted, 0 packets received, 100% packet loss"

    monkeypatch.setattr(
        "app.services.validation_service._run_container_command",
        fake_run_container_command,
    )

    result = _evaluate_live_container_state(
        session=session,
        code="CONNECTIVITY_FAILURE_R3_R4",
        topic="connectivity",
        device="r3",
        error=error,
    )

    assert result is not None
    assert result["passed"] is False
    assert result["evidence"]["validation_mode"] == "live_container_state_check"
    assert result["evidence"]["missing_expected_outputs"] == ["1 packets received"]

