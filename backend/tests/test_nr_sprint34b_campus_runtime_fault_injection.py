import shutil
import subprocess
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.enums import Difficulty, SessionStatus
from app.services.scenario_catalog import CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID, get_scenario
from app.services.session_service import get_lab_session
from app.services.srlinux_runtime_setup import (
    CAMPUS_CLIENT2_EXPECTED_GATEWAY,
    CAMPUS_CLIENT2_INJECTED_GATEWAY,
    CAMPUS_WRONG_CLIENT2_GATEWAY_CODE,
    CAMPUS_WRONG_CLIENT2_GATEWAY_VARIANT_ID,
    apply_srlinux_runtime_setup,
    build_srlinux_runtime_faults,
)
from app.services.topology_generator import GENERATED_DIR
from app.services.validation_service import _run_device_command


def _campus_cli_access(session_id: str = "lab-campus-runtime-fault-test") -> list[dict[str, str]]:
    return [
        {
            "device_id": device,
            "name": device,
            "container_name": f"clab-autonetlab-{session_id}-{device}",
        }
        for device in ["client1", "client2", "srl1", "srl2", "srl3", "srl4"]
    ]


class FakeCompletedProcess:
    def __init__(self, stdout: str = "ok\n", stderr: str = "", returncode: int = 0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def _fake_campus_golden_run(command, **kwargs):
    command_text = " ".join(str(part) for part in command)

    if "client1" in command_text and "ip -4 addr show dev eth1" in command_text:
        return FakeCompletedProcess(stdout="inet 10.10.10.10/24 scope global eth1\n")

    if "client2" in command_text and "ip -4 addr show dev eth1" in command_text:
        return FakeCompletedProcess(stdout="inet 10.10.20.10/24 scope global eth1\n")

    if "client1" in command_text and command_text.endswith(" ip route"):
        return FakeCompletedProcess(stdout="default via 10.10.10.1 dev eth1\n")

    if "client2" in command_text and command_text.endswith(" ip route"):
        return FakeCompletedProcess(stdout="default via 10.10.20.1 dev eth1\n")

    interface_outputs = {
        ("srl1", "ethernet-1/1"): "10.10.10.1/24",
        ("srl1", "ethernet-1/2"): "10.10.13.1/30",
        ("srl1", "ethernet-1/3"): "10.10.14.1/30",
        ("srl2", "ethernet-1/1"): "10.10.20.1/24",
        ("srl2", "ethernet-1/2"): "10.10.23.1/30",
        ("srl2", "ethernet-1/3"): "10.10.24.1/30",
        ("srl3", "ethernet-1/1"): "10.10.13.2/30",
        ("srl3", "ethernet-1/2"): "10.10.23.2/30",
        ("srl4", "ethernet-1/1"): "10.10.14.2/30",
        ("srl4", "ethernet-1/2"): "10.10.24.2/30",
    }

    if "info from state interface" in command_text:
        for (device, interface), ip_address in interface_outputs.items():
            if device in command_text and interface in command_text:
                return FakeCompletedProcess(stdout=f"address {ip_address} {{\n}}\n")

    if "info network-instance default static-routes route" in command_text:
        if "srl1" in command_text and "10.10.20.0/24" in command_text:
            return FakeCompletedProcess(stdout="static-next-hop-group campus-srl1-to-client2\n")
        if "srl2" in command_text and "10.10.10.0/24" in command_text:
            return FakeCompletedProcess(stdout="static-next-hop-group campus-srl2-to-client1\n")
        if "srl3" in command_text and "10.10.10.0/24" in command_text:
            return FakeCompletedProcess(stdout="static-next-hop-group campus-srl3-to-client1\n")
        if "srl3" in command_text and "10.10.20.0/24" in command_text:
            return FakeCompletedProcess(stdout="static-next-hop-group campus-srl3-to-client2\n")
        if "srl4" in command_text and "10.10.10.0/24" in command_text:
            return FakeCompletedProcess(stdout="static-next-hop-group campus-srl4-to-client1\n")
        if "srl4" in command_text and "10.10.20.0/24" in command_text:
            return FakeCompletedProcess(stdout="static-next-hop-group campus-srl4-to-client2\n")

    if "info network-instance default" in command_text:
        return FakeCompletedProcess(
            stdout=(
                "interface ethernet-1/1.0 {\n}\n"
                "interface ethernet-1/2.0 {\n}\n"
                "interface ethernet-1/3.0 {\n}\n"
            )
        )

    if "ping" in command_text and "10.10.20.10" in command_text:
        return FakeCompletedProcess(stdout="64 bytes from 10.10.20.10: icmp_seq=1 ttl=62 time=4.1 ms\n")

    if "ping" in command_text and "10.10.10.10" in command_text:
        return FakeCompletedProcess(stdout="64 bytes from 10.10.10.10: icmp_seq=1 ttl=62 time=4.1 ms\n")

    return FakeCompletedProcess()


def test_nr_sprint34b_campus_catalog_is_runtime_fault_injection_enabled():
    scenario = get_scenario(CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID)

    assert scenario["runtime_profile"] == "runtime_fault_injection"

    notes = "\n".join(scenario["student_notes"])
    assert "hidden, fixable client default-gateway issue" in notes
    assert "No hidden solution data is exposed" in notes


def test_nr_sprint34b_campus_runtime_fault_catalog_defaults_to_client2_wrong_gateway():
    faults = build_srlinux_runtime_faults(
        difficulty=Difficulty.easy,
        seed="lab-campus-fault-catalog",
        scenario_id=CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID,
    )

    assert len(faults) == 1

    fault = faults[0]

    assert fault["code"] == CAMPUS_WRONG_CLIENT2_GATEWAY_CODE
    assert fault["variant_id"] == CAMPUS_WRONG_CLIENT2_GATEWAY_VARIANT_ID
    assert fault["topic"] == "default_gateway"
    assert fault["device"] == "client2"
    assert fault["expected_outputs"] == [f"default via {CAMPUS_CLIENT2_EXPECTED_GATEWAY}"]
    assert fault["injection_commands"] == [
        f"ip route replace default via {CAMPUS_CLIENT2_INJECTED_GATEWAY} dev eth1"
    ]


def test_nr_sprint34b_create_campus_session_stores_internal_fault_metadata_only():
    client = TestClient(app)
    student_id = f"pytest-nr34b-{uuid4().hex[:8]}"

    response = client.post(
        "/api/v1/labs",
        json={
            "student_id": student_id,
            "difficulty": "easy",
            "scenario_id": CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID,
        },
    )

    assert response.status_code == 201

    payload = response.json()
    session_id = payload["session_id"]
    generated_dir = GENERATED_DIR / session_id

    try:
        forbidden_keys = {
            "injected_errors",
            "evidence",
            "debug",
            "solution",
            "validation_command",
            "injection_commands",
        }
        assert forbidden_keys.isdisjoint(payload.keys())
        assert str(CAMPUS_CLIENT2_INJECTED_GATEWAY) not in str(payload)

        session = get_lab_session(session_id)
        injected_errors = session["injected_errors"]

        assert len(injected_errors) == 1

        fault = (
            injected_errors[0].model_dump()
            if hasattr(injected_errors[0], "model_dump")
            else injected_errors[0]
        )

        assert fault["code"] == CAMPUS_WRONG_CLIENT2_GATEWAY_CODE
        assert fault["variant_id"] == CAMPUS_WRONG_CLIENT2_GATEWAY_VARIANT_ID
        assert fault["device"] == "client2"
        assert fault["injection_commands"] == [
            f"ip route replace default via {CAMPUS_CLIENT2_INJECTED_GATEWAY} dev eth1"
        ]
    finally:
        if generated_dir.exists():
            shutil.rmtree(generated_dir)


def test_nr_sprint34b_campus_runtime_setup_injects_client2_wrong_gateway_after_golden(monkeypatch):
    session_id = "lab-campus-runtime-fault-test"
    session = {
        "session_id": session_id,
        "scenario": {"id": CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID},
        "injected_errors": build_srlinux_runtime_faults(
            difficulty=Difficulty.easy,
            seed=session_id,
            scenario_id=CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID,
        ),
        "cli_access": _campus_cli_access(session_id),
    }

    executed_display_commands = []

    def fake_run(command, **kwargs):
        command_text = " ".join(str(part) for part in command)

        if command_text.startswith("docker exec"):
            if " sh -lc " in command_text:
                executed_display_commands.append(command_text.split(" sh -lc ", 1)[1])
            elif " sr_cli" in command_text:
                executed_display_commands.append("sr_cli")

        return _fake_campus_golden_run(command, **kwargs)

    monkeypatch.setattr(
        "app.services.srlinux_runtime_setup.subprocess.run",
        fake_run,
    )

    result = apply_srlinux_runtime_setup(session)

    assert result["success"] is True
    assert result["status"] == SessionStatus.deployed
    assert result["message"] == (
        "SR Linux campus golden runtime setup and runtime fault injection applied successfully."
    )

    golden_command = "ip route replace default via 10.10.20.1 dev eth1"
    injected_command = "ip route replace default via 10.10.20.254 dev eth1"

    assert golden_command in executed_display_commands
    assert injected_command in executed_display_commands
    assert executed_display_commands.index(injected_command) > executed_display_commands.index(golden_command)


def test_nr_sprint34b_live_validation_timeout_outputs_are_string_normalized(monkeypatch):
    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(
            cmd=["docker", "exec", "container", "sh", "-lc", "ping"],
            timeout=20,
            output=b"partial stdout",
            stderr=b"partial stderr",
        )

    monkeypatch.setattr(
        "app.services.validation_service.subprocess.run",
        fake_run,
    )

    observed = _run_device_command(
        container_name="container",
        command=["sh", "-lc", "ping"],
        timeout=1,
    )

    assert observed["return_code"] is None
    assert observed["stdout"] == "partial stdout"
    assert observed["stderr"] == "partial stderr"
    assert observed["output"] == "partial stdout\\npartial stderr"
