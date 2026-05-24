from app.schemas.enums import SessionStatus
from app.services.runtime_error_injection import apply_runtime_error_injection


def test_runtime_error_injection_applies_baseline_before_selected_errors(monkeypatch):
    calls = []

    session = {
        "session_id": "lab-runtime-test",
        "cli_access": [
            {
                "device_id": "r1",
                "name": "r1",
                "container_name": "clab-autonetlab-lab-runtime-test-r1",
            },
            {
                "device_id": "r2",
                "name": "r2",
                "container_name": "clab-autonetlab-lab-runtime-test-r2",
            },
        ],
        "injected_errors": [
            {
                "code": "INTERFACE_DOWN_R2",
                "topic": "interface_status",
                "device": "r2",
                "variant_id": "r2_eth1_shutdown",
                "injection_commands": ["ip link set eth1 down"],
            }
        ],
    }

    def fake_run_container_command(container_name: str, command: str):
        calls.append((container_name, command))
        return {
            "return_code": 0,
            "stdout": "",
            "stderr": "",
        }

    monkeypatch.setattr(
        "app.services.runtime_error_injection._run_container_command",
        fake_run_container_command,
    )

    result = apply_runtime_error_injection(session)

    assert result["success"] is True
    assert result["status"] == SessionStatus.deployed
    assert any("10.10.12.1/24" in command for _, command in calls)
    assert calls[-1] == (
        "clab-autonetlab-lab-runtime-test-r2",
        "ip link set eth1 down",
    )


def test_runtime_error_injection_returns_error_when_command_fails(monkeypatch):
    session = {
        "session_id": "lab-runtime-fail",
        "cli_access": [
            {
                "device_id": "r1",
                "name": "r1",
                "container_name": "clab-autonetlab-lab-runtime-fail-r1",
            }
        ],
        "injected_errors": [],
    }

    def fake_run_container_command(container_name: str, command: str):
        return {
            "return_code": 1,
            "stdout": "",
            "stderr": "forced failure",
        }

    monkeypatch.setattr(
        "app.services.runtime_error_injection._run_container_command",
        fake_run_container_command,
    )

    result = apply_runtime_error_injection(session)

    assert result["success"] is False
    assert result["status"] == SessionStatus.error
    assert result["error_code"] == "RUNTIME_BASELINE_COMMAND_FAILED"
