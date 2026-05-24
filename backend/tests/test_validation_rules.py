from app.services.error_injection import ERROR_POOL
from app.services.validation_rules import (
    ERROR_VALIDATION_RULES,
    get_live_validation_rule,
    supported_live_validation_codes,
)
from app.services.validation_service import _evaluate_live_container_state


def test_every_error_pool_code_has_live_validation_rule():
    error_codes = {
        error["code"]
        for error in ERROR_POOL
    }

    assert error_codes <= supported_live_validation_codes()


def test_live_validation_rule_catalog_has_no_empty_expectations():
    for code, rule in ERROR_VALIDATION_RULES.items():
        assert code
        assert rule.command
        assert rule.expected_outputs
        assert all(expected for expected in rule.expected_outputs)


def test_get_live_validation_rule_returns_none_for_unknown_code():
    assert get_live_validation_rule("UNKNOWN_ERROR_CODE") is None


def test_live_validation_uses_catalog_rule(monkeypatch):
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
    assert result["evidence"]["validation_mode"] == "live_container_state_check"
    assert result["evidence"]["command"] == "ip addr show eth1"
    assert result["evidence"]["expected_state"] == "inet 10.10.12.1/24"


def test_live_validation_reports_missing_expected_output(monkeypatch):
    session = {
        "cli_access": [
            {
                "device_id": "r1",
                "name": "r1",
                "container_name": "clab-autonetlab-test-r1",
            }
        ]
    }

    monkeypatch.setattr(
        "app.services.validation_service._run_container_command",
        lambda container_name, command: "inet 10.10.10.99/24 scope global eth1",
    )

    result = _evaluate_live_container_state(
        session=session,
        code="IP_ADDRESS_MISMATCH",
        topic="ip_addressing",
        device="r1",
    )

    assert result is not None
    assert result["passed"] is False
    assert result["evidence"]["missing_expected_outputs"] == ["inet 10.10.12.1/24"]
