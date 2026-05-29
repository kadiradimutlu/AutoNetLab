import shutil
from pathlib import Path

import yaml
from fastapi import HTTPException

from app.schemas.enums import Difficulty, SessionStatus
from app.services.scenario_catalog import (
    SR_BASIC_LINK_SCENARIO_ID,
    get_scenario,
    is_srlinux_scenario,
    list_scenarios,
)
from app.services.topology_generator import GENERATED_DIR, generate_session_topology


def test_scenario_catalog_exposes_srlinux_basic_link():
    scenarios = list_scenarios()

    scenario = next(
        item
        for item in scenarios
        if item["id"] == SR_BASIC_LINK_SCENARIO_ID
    )

    assert scenario["router_os"] == "Nokia SR Linux"
    assert scenario["topology_template"] == "srl-basic-link"
    assert scenario["addressing_table"]
    assert scenario["routing_requirements"]
    assert scenario["expected_connectivity"]
    assert is_srlinux_scenario(SR_BASIC_LINK_SCENARIO_ID) is True


def test_unknown_scenario_rejected():
    try:
        get_scenario("does-not-exist")
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "Unsupported scenario_id" in str(exc.detail)
    else:
        raise AssertionError("Unknown scenario_id should raise HTTPException.")


def test_generate_srlinux_basic_link_topology_file():
    session_id = "lab-sprint30-srl-test"
    generated_dir = GENERATED_DIR / session_id

    if generated_dir.exists():
        shutil.rmtree(generated_dir)

    try:
        result = generate_session_topology(
            session_id=session_id,
            difficulty=Difficulty.easy,
            topology_template="basic-two-router",
            scenario_id=SR_BASIC_LINK_SCENARIO_ID,
        )

        topology = result["topology"]
        topology_file = Path(result["topology_file"])

        assert result["topology_template"] == "srl-basic-link"
        assert topology_file.exists()

        node_by_id = {
            node.id: node
            for node in topology.nodes
        }

        assert node_by_id["srl1"].kind == "nokia_srlinux"
        assert node_by_id["srl1"].image == "ghcr.io/nokia/srlinux:26.3.2"
        assert node_by_id["client1"].kind == "linux"
        assert node_by_id["client1"].image == "ghcr.io/srl-labs/network-multitool:latest"

        payload = yaml.safe_load(topology_file.read_text(encoding="utf-8"))

        assert payload["topology"]["nodes"]["srl1"]["kind"] == "nokia_srlinux"
        assert payload["topology"]["nodes"]["srl1"]["type"] == "ixr-d2l"
        assert payload["topology"]["nodes"]["client1"]["kind"] == "linux"
        assert payload["topology"]["links"][0]["endpoints"] == [
            "srl1:e1-1",
            "client1:eth1",
        ]
        assert payload["topology"]["links"][0]["ipv4"] == [
            "10.10.10.1/24",
            "10.10.10.10/24",
        ]
    finally:
        if generated_dir.exists():
            shutil.rmtree(generated_dir)


def test_meta_scenarios_api_exposes_srlinux_catalog():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)

    response = client.get("/api/v1/meta/scenarios")

    assert response.status_code == 200

    payload = response.json()
    assert payload["success"] is True
    assert payload["message"] == "Scenario catalog retrieved successfully."

    scenario_by_id = {
        scenario["id"]: scenario
        for scenario in payload["scenarios"]
    }

    scenario = scenario_by_id[SR_BASIC_LINK_SCENARIO_ID]

    assert scenario["title"] == "SR Linux Basic Link Troubleshooting"
    assert scenario["router_os"] == "Nokia SR Linux"
    assert scenario["addressing_table"]
    assert scenario["routing_requirements"]
    assert scenario["expected_connectivity"]


def test_create_lab_with_srlinux_scenario_returns_student_safe_contract():
    from uuid import uuid4

    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    student_id = f"pytest-sprint30-{uuid4().hex[:8]}"

    response = client.post(
        "/api/v1/labs",
        json={
            "student_id": student_id,
            "difficulty": "easy",
            "scenario_id": SR_BASIC_LINK_SCENARIO_ID,
        },
    )

    assert response.status_code == 201

    payload = response.json()
    session_id = payload["session_id"]
    generated_dir = GENERATED_DIR / session_id

    try:
        assert payload["scenario"]["id"] == SR_BASIC_LINK_SCENARIO_ID
        assert payload["scenario"]["addressing_table"]
        assert payload["scenario"]["routing_requirements"]
        assert payload["scenario"]["expected_connectivity"]

        assert "injected_errors" not in payload
        assert "runtime_cleanup_history" not in payload

        node_by_id = {
            node["id"]: node
            for node in payload["topology"]["nodes"]
        }

        assert node_by_id["srl1"]["kind"] == "nokia_srlinux"
        assert node_by_id["srl1"]["image"] == "ghcr.io/nokia/srlinux:26.3.2"
        assert node_by_id["client1"]["kind"] == "linux"

        cli_by_device = {
            item["device_id"]: item
            for item in payload["cli_access"]
        }

        assert "sr_cli" in cli_by_device["srl1"]["command"]
        assert cli_by_device["client1"]["command"].endswith(" sh")

        topology_file = generated_dir / "lab.clab.yml"
        assert topology_file.exists()
        assert "nokia_srlinux" in topology_file.read_text(encoding="utf-8")
    finally:
        if generated_dir.exists():
            shutil.rmtree(generated_dir)


def test_srlinux_runtime_setup_applies_client_ip_gateway_and_network_instance(monkeypatch):
    from app.services.srlinux_runtime_setup import apply_srlinux_runtime_setup

    session = {
        "session_id": "lab-runtime-setup-test",
        "scenario": {"id": SR_BASIC_LINK_SCENARIO_ID},
        "cli_access": [
            {
                "device_id": "srl1",
                "name": "srl1",
                "container_name": "clab-autonetlab-lab-runtime-setup-test-srl1",
            },
            {
                "device_id": "client1",
                "name": "client1",
                "container_name": "clab-autonetlab-lab-runtime-setup-test-client1",
            },
        ],
    }

    executed_commands = []
    sr_cli_input = []

    class FakeCompletedProcess:
        def __init__(self, stdout: str = "", returncode: int = 0):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = ""

    def fake_run(command, **kwargs):
        command_text = " ".join(command)
        executed_commands.append(command_text)

        if kwargs.get("input"):
            sr_cli_input.append(kwargs["input"])

        if "ip -4 addr show dev eth1" in command_text:
            return FakeCompletedProcess(stdout="inet 10.10.10.10/24 scope global eth1\n")

        if "ip route" in command_text:
            return FakeCompletedProcess(stdout="default via 10.10.10.1 dev eth1\n")

        if "info from state interface ethernet-1/1 subinterface 0 ipv4" in command_text:
            return FakeCompletedProcess(stdout="address 10.10.10.1/24 {\n    origin static\n}\n")

        if "info network-instance default" in command_text:
            return FakeCompletedProcess(stdout="interface ethernet-1/1.0 {\n}\n")

        if "ping" in command_text and "10.10.10.1" in command_text:
            return FakeCompletedProcess(
                stdout="64 bytes from 10.10.10.1: icmp_seq=1 ttl=64 time=8.1 ms\n"
            )

        return FakeCompletedProcess(stdout="ok\n")

    monkeypatch.setattr(
        "app.services.srlinux_runtime_setup.subprocess.run",
        fake_run,
    )

    result = apply_srlinux_runtime_setup(session)

    assert result["success"] is True
    assert result["status"].value == "deployed"
    assert result["message"] == "SR Linux runtime setup applied successfully."

    joined_commands = "\n".join(executed_commands)
    joined_sr_cli_input = "\n".join(sr_cli_input)

    assert "docker exec -i clab-autonetlab-lab-runtime-setup-test-srl1 sr_cli" in joined_commands
    assert "set network-instance default interface ethernet-1/1.0" in joined_sr_cli_input
    assert "commit now" in joined_sr_cli_input

    assert "ip addr add 10.10.10.10/24 dev eth1" in joined_commands
    assert "ip route replace default via 10.10.10.1 dev eth1" in joined_commands
    assert "ping" in joined_commands
    assert "10.10.10.1" in joined_commands


def test_srlinux_runtime_setup_fails_when_gateway_ping_fails(monkeypatch):
    from app.services.srlinux_runtime_setup import apply_srlinux_runtime_setup

    session = {
        "session_id": "lab-runtime-setup-fail-test",
        "scenario": {"id": SR_BASIC_LINK_SCENARIO_ID},
        "cli_access": [
            {
                "device_id": "srl1",
                "name": "srl1",
                "container_name": "clab-autonetlab-lab-runtime-setup-fail-test-srl1",
            },
            {
                "device_id": "client1",
                "name": "client1",
                "container_name": "clab-autonetlab-lab-runtime-setup-fail-test-client1",
            },
        ],
    }

    class FakeCompletedProcess:
        def __init__(self, stdout: str = "", returncode: int = 0):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = ""

    def fake_run(command, **kwargs):
        command_text = " ".join(command)

        if "ip -4 addr show dev eth1" in command_text:
            return FakeCompletedProcess(stdout="inet 10.10.10.10/24 scope global eth1\n")

        if "ip route" in command_text:
            return FakeCompletedProcess(stdout="default via 10.10.10.1 dev eth1\n")

        if "info from state interface ethernet-1/1 subinterface 0 ipv4" in command_text:
            return FakeCompletedProcess(stdout="address 10.10.10.1/24 {\n    origin static\n}\n")

        if "info network-instance default" in command_text:
            return FakeCompletedProcess(stdout="interface ethernet-1/1.0 {\n}\n")

        if "ping" in command_text and "10.10.10.1" in command_text:
            return FakeCompletedProcess(
                stdout="3 packets transmitted, 0 received, 100% packet loss\n",
                returncode=1,
            )

        return FakeCompletedProcess(stdout="ok\n")

    monkeypatch.setattr(
        "app.services.srlinux_runtime_setup.subprocess.run",
        fake_run,
    )

    result = apply_srlinux_runtime_setup(session)

    assert result["success"] is False
    assert result["status"].value == "error"
    assert result["error_code"] == "SRLINUX_RUNTIME_VERIFICATION_FAILED"
    assert "ping" in result["detail"]



def test_srlinux_validation_passes_when_live_state_matches(monkeypatch):
    from app.services.validation_service import validate_session

    session = {
        "session_id": "lab-srl-validation-pass",
        "status": SessionStatus.deployed,
        "scenario": {"id": SR_BASIC_LINK_SCENARIO_ID},
        "topology_template": "srl-basic-link",
        "cli_access": [
            {
                "device_id": "srl1",
                "name": "srl1",
                "container_name": "clab-autonetlab-lab-srl-validation-pass-srl1",
            },
            {
                "device_id": "client1",
                "name": "client1",
                "container_name": "clab-autonetlab-lab-srl-validation-pass-client1",
            },
        ],
        "injected_errors": [],
    }

    class FakeCompletedProcess:
        def __init__(self, stdout: str = "", returncode: int = 0):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = ""

    def fake_run(command, **kwargs):
        command_text = " ".join(command)

        if "info from state interface ethernet-1/1 subinterface 0 ipv4" in command_text:
            return FakeCompletedProcess(stdout="address 10.10.10.1/24 {\n    origin static\n}\n")

        if "info network-instance default" in command_text:
            return FakeCompletedProcess(stdout="interface ethernet-1/1.0 {\n}\n")

        if "ip -4 addr show dev eth1" in command_text:
            return FakeCompletedProcess(stdout="inet 10.10.10.10/24 scope global eth1\n")

        if "ip route" in command_text:
            return FakeCompletedProcess(stdout="default via 10.10.10.1 dev eth1\n")

        if "ping" in command_text and "10.10.10.1" in command_text:
            return FakeCompletedProcess(stdout="64 bytes from 10.10.10.1: icmp_seq=1 ttl=64 time=2.1 ms\n")

        return FakeCompletedProcess(stdout="unexpected command\n", returncode=1)

    monkeypatch.setattr(
        "app.services.validation_service.subprocess.run",
        fake_run,
    )

    result = validate_session(session)

    assert result.status == SessionStatus.validated
    assert result.passed is True
    assert result.score == 100
    assert len(result.checks) == 5
    assert all(check.passed for check in result.checks)
    assert all(check.max_points == 20 for check in result.checks)
    assert result.recommendations == ["All validation checks passed. Good job."]

    evidence_modes = {
        check.evidence["validation_mode"]
        for check in result.checks
    }

    assert evidence_modes == {"srlinux_live_state_check"}


def test_srlinux_validation_fails_when_client_default_gateway_is_wrong(monkeypatch):
    from app.services.validation_service import validate_session

    session = {
        "session_id": "lab-srl-validation-fail",
        "status": SessionStatus.deployed,
        "scenario": {"id": SR_BASIC_LINK_SCENARIO_ID},
        "topology_template": "srl-basic-link",
        "cli_access": [
            {
                "device_id": "srl1",
                "name": "srl1",
                "container_name": "clab-autonetlab-lab-srl-validation-fail-srl1",
            },
            {
                "device_id": "client1",
                "name": "client1",
                "container_name": "clab-autonetlab-lab-srl-validation-fail-client1",
            },
        ],
        "injected_errors": [],
    }

    class FakeCompletedProcess:
        def __init__(self, stdout: str = "", returncode: int = 0):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = ""

    def fake_run(command, **kwargs):
        command_text = " ".join(command)

        if "info from state interface ethernet-1/1 subinterface 0 ipv4" in command_text:
            return FakeCompletedProcess(stdout="address 10.10.10.1/24 {\n    origin static\n}\n")

        if "info network-instance default" in command_text:
            return FakeCompletedProcess(stdout="interface ethernet-1/1.0 {\n}\n")

        if "ip -4 addr show dev eth1" in command_text:
            return FakeCompletedProcess(stdout="inet 10.10.10.10/24 scope global eth1\n")

        if "ip route" in command_text:
            return FakeCompletedProcess(stdout="default via 172.20.20.1 dev eth0\n")

        if "ping" in command_text and "10.10.10.1" in command_text:
            return FakeCompletedProcess(stdout="64 bytes from 10.10.10.1: icmp_seq=1 ttl=64 time=2.1 ms\n")

        return FakeCompletedProcess(stdout="unexpected command\n", returncode=1)

    monkeypatch.setattr(
        "app.services.validation_service.subprocess.run",
        fake_run,
    )

    result = validate_session(session)

    assert result.status == SessionStatus.validated
    assert result.passed is False
    assert result.score == 80

    failed_checks = [
        check
        for check in result.checks
        if not check.passed
    ]

    assert len(failed_checks) == 1
    assert failed_checks[0].check_id == "srl_check_4_client_default_gateway"
    assert failed_checks[0].topic == "default_gateway"
    assert "Review and fix topic: Default Gateway" in result.recommendations



def test_srlinux_runtime_fault_catalog_defaults_to_wrong_client_gateway():
    from app.services.srlinux_runtime_setup import (
        SRLINUX_WRONG_CLIENT_GATEWAY_CODE,
        SRLINUX_WRONG_CLIENT_GATEWAY_VARIANT_ID,
        build_srlinux_runtime_faults,
    )

    faults = build_srlinux_runtime_faults(
        difficulty=Difficulty.easy,
        seed="lab-srl-fault-catalog",
    )

    assert len(faults) == 1

    fault = faults[0]

    assert fault["code"] == SRLINUX_WRONG_CLIENT_GATEWAY_CODE
    assert fault["variant_id"] == SRLINUX_WRONG_CLIENT_GATEWAY_VARIANT_ID
    assert fault["topic"] == "default_gateway"
    assert fault["device"] == "client1"
    assert fault["expected_outputs"] == ["default via 10.10.10.1"]
    assert fault["injection_commands"] == [
        "ip route replace default via 10.10.10.254 dev eth1"
    ]


def test_create_srlinux_session_stores_internal_runtime_fault_metadata():
    from uuid import uuid4

    from fastapi.testclient import TestClient

    from app.main import app
    from app.services.session_service import get_lab_session

    client = TestClient(app)
    student_id = f"pytest-sprint30e-{uuid4().hex[:8]}"

    response = client.post(
        "/api/v1/labs",
        json={
            "student_id": student_id,
            "difficulty": "easy",
            "scenario_id": SR_BASIC_LINK_SCENARIO_ID,
        },
    )

    assert response.status_code == 201

    payload = response.json()
    session_id = payload["session_id"]
    generated_dir = GENERATED_DIR / session_id

    try:
        assert "injected_errors" not in payload

        session = get_lab_session(session_id)
        injected_errors = session["injected_errors"]

        assert len(injected_errors) == 1

        fault = (
            injected_errors[0].model_dump()
            if hasattr(injected_errors[0], "model_dump")
            else injected_errors[0]
        )

        assert fault["code"] == "SRLINUX_WRONG_CLIENT_GATEWAY"
        assert fault["topic"] == "default_gateway"
        assert fault["device"] == "client1"
        assert fault["injection_commands"] == [
            "ip route replace default via 10.10.10.254 dev eth1"
        ]
    finally:
        if generated_dir.exists():
            shutil.rmtree(generated_dir)


def test_srlinux_runtime_setup_injects_wrong_client_gateway_after_baseline(monkeypatch):
    from app.services.srlinux_runtime_setup import (
        apply_srlinux_runtime_setup,
        build_srlinux_runtime_faults,
    )

    session = {
        "session_id": "lab-runtime-fault-injection-test",
        "scenario": {"id": SR_BASIC_LINK_SCENARIO_ID},
        "injected_errors": build_srlinux_runtime_faults(
            difficulty=Difficulty.easy,
            seed="lab-runtime-fault-injection-test",
        ),
        "cli_access": [
            {
                "device_id": "srl1",
                "name": "srl1",
                "container_name": "clab-autonetlab-lab-runtime-fault-injection-test-srl1",
            },
            {
                "device_id": "client1",
                "name": "client1",
                "container_name": "clab-autonetlab-lab-runtime-fault-injection-test-client1",
            },
        ],
    }

    executed_commands = []
    wrong_gateway_applied = {"value": False}

    class FakeCompletedProcess:
        def __init__(self, stdout: str = "", returncode: int = 0):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = ""

    def fake_run(command, **kwargs):
        input_text = kwargs.get("input") or ""
        command_text = " ".join(command)
        combined = f"{command_text}\n{input_text}"
        executed_commands.append(combined)

        if "ip route replace default via 10.10.10.254 dev eth1" in command_text:
            wrong_gateway_applied["value"] = True
            return FakeCompletedProcess(stdout="fault injected\n")

        if "ip -4 addr show dev eth1" in command_text:
            return FakeCompletedProcess(stdout="inet 10.10.10.10/24 scope global eth1\n")

        if "ip route" in command_text:
            if wrong_gateway_applied["value"]:
                return FakeCompletedProcess(stdout="default via 10.10.10.254 dev eth1\n")
            return FakeCompletedProcess(stdout="default via 10.10.10.1 dev eth1\n")

        if "info from state interface ethernet-1/1 subinterface 0 ipv4" in command_text:
            return FakeCompletedProcess(stdout="address 10.10.10.1/24 {\n    origin static\n}\n")

        if "info network-instance default" in command_text:
            return FakeCompletedProcess(stdout="interface ethernet-1/1.0 {\n}\n")

        if "ping" in command_text and "10.10.10.1" in command_text:
            return FakeCompletedProcess(stdout="64 bytes from 10.10.10.1: icmp_seq=1 ttl=64 time=2.1 ms\n")

        return FakeCompletedProcess(stdout="ok\n")

    monkeypatch.setattr(
        "app.services.srlinux_runtime_setup.subprocess.run",
        fake_run,
    )

    result = apply_srlinux_runtime_setup(session)
    joined_commands = "\n".join(executed_commands)

    assert result["success"] is True
    assert result["status"] == SessionStatus.deployed
    assert "ip route replace default via 10.10.10.1 dev eth1" in joined_commands
    assert "ip route replace default via 10.10.10.254 dev eth1" in joined_commands
    assert wrong_gateway_applied["value"] is True

def test_srlinux_validation_fails_only_default_gateway_when_wrong_gateway_is_on_connected_subnet(monkeypatch):
    from app.services.validation_service import validate_session

    session = {
        "session_id": "lab-srl-validation-realistic-fail",
        "status": SessionStatus.deployed,
        "scenario": {"id": SR_BASIC_LINK_SCENARIO_ID},
        "topology_template": "srl-basic-link",
        "cli_access": [
            {
                "device_id": "srl1",
                "name": "srl1",
                "container_name": "clab-autonetlab-lab-srl-validation-realistic-fail-srl1",
            },
            {
                "device_id": "client1",
                "name": "client1",
                "container_name": "clab-autonetlab-lab-srl-validation-realistic-fail-client1",
            },
        ],
        "injected_errors": [],
    }

    class FakeCompletedProcess:
        def __init__(self, stdout: str = "", returncode: int = 0):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = ""

    def fake_run(command, **kwargs):
        command_text = " ".join(command)

        if "info from state interface ethernet-1/1 subinterface 0 ipv4" in command_text:
            return FakeCompletedProcess(
                stdout="""address 10.10.10.1/24 {
    origin static
}
"""
            )

        if "info network-instance default" in command_text:
            return FakeCompletedProcess(
                stdout="""interface ethernet-1/1.0 {
}
"""
            )

        if "ip -4 addr show dev eth1" in command_text:
            return FakeCompletedProcess(
                stdout="inet 10.10.10.10/24 scope global eth1\n"
            )

        if "ip route" in command_text:
            return FakeCompletedProcess(
                stdout=(
                    "default via 10.10.10.254 dev eth1\n"
                    "10.10.10.0/24 dev eth1 proto kernel scope link src 10.10.10.10\n"
                )
            )

        if "ping" in command_text and "10.10.10.1" in command_text:
            return FakeCompletedProcess(
                stdout="64 bytes from 10.10.10.1: icmp_seq=1 ttl=64 time=2.1 ms\n"
            )

        return FakeCompletedProcess(stdout="unexpected command\n", returncode=1)

    monkeypatch.setattr(
        "app.services.validation_service.subprocess.run",
        fake_run,
    )

    result = validate_session(session)

    assert result.status == SessionStatus.validated
    assert result.passed is False
    assert result.score == 80

    failed_check_ids = {
        check.check_id
        for check in result.checks
        if not check.passed
    }

    assert failed_check_ids == {
        "srl_check_4_client_default_gateway",
    }

    connectivity_check = next(
        check
        for check in result.checks
        if check.check_id == "srl_check_5_gateway_connectivity"
    )

    assert connectivity_check.passed is True
    assert "Review and fix topic: Default Gateway" in result.recommendations
    assert "Review and fix topic: Connectivity" not in result.recommendations
