from app.schemas.enums import Difficulty, SessionStatus
from app.services.scenario_catalog import (
    BRANCH_STATIC_ROUTING_SCENARIO_ID,
    CAMPUS_CORE_ROUTING_SCENARIO_ID,
    CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID,
    SR_BASIC_LINK_SCENARIO_ID,
    SR_EDGE_LINK_SCENARIO_ID,
)
from app.services.srlinux_runtime_setup import (
    BRANCH_CLIENT2_INJECTED_GATEWAY,
    BRANCH_CLIENT2_EXPECTED_GATEWAY,
    BRANCH_WRONG_CLIENT2_GATEWAY_CODE,
    CAMPUS_WRONG_CLIENT2_GATEWAY_CODE,
    SRLINUX_WRONG_CLIENT_GATEWAY_CODE,
    apply_srlinux_runtime_setup,
    build_srlinux_runtime_faults,
)
from app.services.validation_service import validate_session


def _cli_access(session_id: str, devices: list[str]) -> list[dict]:
    return [
        {
            "device_id": device,
            "name": device,
            "container_name": f"clab-autonetlab-{session_id}-{device}",
        }
        for device in devices
    ]


class FakeCompletedProcess:
    def __init__(self, stdout: str = "ok\n", returncode: int = 0):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = ""


def _fake_branch_golden_run(command, **kwargs):
    command_text = " ".join(str(part) for part in command)

    if "ip -4 addr show dev eth1" in command_text and "-client1" in command_text:
        return FakeCompletedProcess(stdout="inet 10.10.10.10/24 scope global eth1\n")

    if "ip -4 addr show dev eth1" in command_text and "-client2" in command_text:
        return FakeCompletedProcess(stdout="inet 10.10.20.10/24 scope global eth1\n")

    if "ip route" in command_text and "-client1" in command_text:
        return FakeCompletedProcess(stdout="default via 10.10.10.1 dev eth1\n")

    if "ip route" in command_text and "-client2" in command_text:
        return FakeCompletedProcess(stdout="default via 10.10.20.1 dev eth1\n")

    if "info from state interface ethernet-1/1 subinterface 0 ipv4" in command_text and "-srl1" in command_text:
        return FakeCompletedProcess(stdout="address 10.10.10.1/24 {\n}\n")

    if "info from state interface ethernet-1/2 subinterface 0 ipv4" in command_text and "-srl1" in command_text:
        return FakeCompletedProcess(stdout="address 10.10.12.1/30 {\n}\n")

    if "info from state interface ethernet-1/1 subinterface 0 ipv4" in command_text and "-srl2" in command_text:
        return FakeCompletedProcess(stdout="address 10.10.20.1/24 {\n}\n")

    if "info from state interface ethernet-1/2 subinterface 0 ipv4" in command_text and "-srl2" in command_text:
        return FakeCompletedProcess(stdout="address 10.10.12.2/30 {\n}\n")

    if "info network-instance default static-routes route 10.10.20.0/24" in command_text:
        return FakeCompletedProcess(stdout="static-next-hop-group branch-srl1-to-client2\n")

    if "info network-instance default static-routes route 10.10.10.0/24" in command_text:
        return FakeCompletedProcess(stdout="static-next-hop-group branch-srl2-to-client1\n")

    if "info network-instance default" in command_text:
        return FakeCompletedProcess(
            stdout=(
                "interface ethernet-1/1.0 {\n}\n"
                "interface ethernet-1/2.0 {\n}\n"
            )
        )

    if "ping" in command_text and "10.10.20.10" in command_text:
        return FakeCompletedProcess(stdout="64 bytes from 10.10.20.10: icmp_seq=1 ttl=64 time=1 ms\n")

    if "ping" in command_text and "10.10.10.10" in command_text:
        return FakeCompletedProcess(stdout="64 bytes from 10.10.10.10: icmp_seq=1 ttl=64 time=1 ms\n")

    return FakeCompletedProcess()


def test_checkpoint2_fault_builder_supports_canonical_edge_branch_and_campus_ids():
    edge_faults = build_srlinux_runtime_faults(
        difficulty=Difficulty.easy,
        seed="lab-edge",
        scenario_id=SR_EDGE_LINK_SCENARIO_ID,
    )
    branch_faults = build_srlinux_runtime_faults(
        difficulty=Difficulty.easy,
        seed="lab-branch",
        scenario_id=BRANCH_STATIC_ROUTING_SCENARIO_ID,
    )
    campus_faults = build_srlinux_runtime_faults(
        difficulty=Difficulty.easy,
        seed="lab-campus",
        scenario_id=CAMPUS_CORE_ROUTING_SCENARIO_ID,
    )

    assert edge_faults[0]["code"] == SRLINUX_WRONG_CLIENT_GATEWAY_CODE
    assert branch_faults[0]["code"] == BRANCH_WRONG_CLIENT2_GATEWAY_CODE
    assert branch_faults[0]["device"] == "client2"
    assert branch_faults[0]["expected_outputs"] == [
        f"default via {BRANCH_CLIENT2_EXPECTED_GATEWAY}"
    ]
    assert branch_faults[0]["injection_commands"] == [
        f"ip route replace default via {BRANCH_CLIENT2_INJECTED_GATEWAY} dev eth1"
    ]
    assert campus_faults[0]["code"] == CAMPUS_WRONG_CLIENT2_GATEWAY_CODE


def test_checkpoint2_legacy_alias_fault_builder_still_maps_to_canonical_scenarios():
    edge_faults = build_srlinux_runtime_faults(
        difficulty=Difficulty.easy,
        seed="lab-edge-legacy",
        scenario_id=SR_BASIC_LINK_SCENARIO_ID,
    )
    campus_faults = build_srlinux_runtime_faults(
        difficulty=Difficulty.easy,
        seed="lab-campus-legacy",
        scenario_id=CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID,
    )

    assert edge_faults[0]["code"] == SRLINUX_WRONG_CLIENT_GATEWAY_CODE
    assert campus_faults[0]["code"] == CAMPUS_WRONG_CLIENT2_GATEWAY_CODE


def test_checkpoint2_branch_runtime_setup_applies_golden_then_hidden_fault(monkeypatch):
    session_id = "lab-branch-runtime-test"
    executed_commands = []

    def fake_run(command, **kwargs):
        command_text = " ".join(str(part) for part in command)

        if command_text.startswith("docker exec"):
            if " sh -lc " in command_text:
                executed_commands.append(command_text.split(" sh -lc ", 1)[1])
            elif " sr_cli" in command_text:
                executed_commands.append("sr_cli")

        return _fake_branch_golden_run(command, **kwargs)

    monkeypatch.setattr(
        "app.services.srlinux_runtime_setup.subprocess.run",
        fake_run,
    )

    session = {
        "session_id": session_id,
        "scenario": {"id": BRANCH_STATIC_ROUTING_SCENARIO_ID},
        "injected_errors": build_srlinux_runtime_faults(
            difficulty=Difficulty.easy,
            seed=session_id,
            scenario_id=BRANCH_STATIC_ROUTING_SCENARIO_ID,
        ),
        "cli_access": _cli_access(session_id, ["client1", "client2", "srl1", "srl2"]),
    }

    result = apply_srlinux_runtime_setup(session)

    assert result["success"] is True
    assert result["status"] == SessionStatus.deployed
    assert result["message"] == (
        "SR Linux branch static routing golden runtime setup and runtime fault injection applied successfully."
    )

    golden_command = "ip route replace default via 10.10.20.1 dev eth1"
    injected_command = "ip route replace default via 10.10.20.254 dev eth1"

    assert golden_command in executed_commands
    assert injected_command in executed_commands
    assert executed_commands.index(injected_command) > executed_commands.index(golden_command)


def test_checkpoint2_branch_live_validation_passes_when_golden_state_matches(monkeypatch):
    monkeypatch.setattr(
        "app.services.validation_service.subprocess.run",
        _fake_branch_golden_run,
    )

    session = {
        "session_id": "lab-branch-validation-pass",
        "status": SessionStatus.deployed,
        "scenario": {"id": BRANCH_STATIC_ROUTING_SCENARIO_ID},
        "topology_template": BRANCH_STATIC_ROUTING_SCENARIO_ID,
        "cli_access": _cli_access(
            "lab-branch-validation-pass",
            ["client1", "client2", "srl1", "srl2"],
        ),
    }

    result = validate_session(session)

    assert result.passed is True
    assert result.score == 100
    assert len(result.checks) == 8
    assert {check.check_id for check in result.checks} == {
        "branch_check_1_client1_address",
        "branch_check_2_client1_default_gateway",
        "branch_check_3_client2_address",
        "branch_check_4_client2_default_gateway",
        "branch_check_5_client1_to_client2_connectivity",
        "branch_check_6_client2_to_client1_connectivity",
        "branch_check_7_srl1_route_to_client2",
        "branch_check_8_srl2_route_to_client1",
    }


def test_checkpoint2_branch_live_validation_detects_wrong_client2_gateway(monkeypatch):
    def fake_run(command, **kwargs):
        command_text = " ".join(str(part) for part in command)

        if "ip route" in command_text and "-client2" in command_text:
            return FakeCompletedProcess(stdout="default via 10.10.20.254 dev eth1\n")

        if "ping" in command_text and "-client2" in command_text and "10.10.10.10" in command_text:
            return FakeCompletedProcess(stdout="3 packets transmitted, 0 received, 100% packet loss\n", returncode=1)

        return _fake_branch_golden_run(command, **kwargs)

    monkeypatch.setattr(
        "app.services.validation_service.subprocess.run",
        fake_run,
    )

    session = {
        "session_id": "lab-branch-validation-fail",
        "status": SessionStatus.deployed,
        "scenario": {"id": BRANCH_STATIC_ROUTING_SCENARIO_ID},
        "topology_template": BRANCH_STATIC_ROUTING_SCENARIO_ID,
        "cli_access": _cli_access(
            "lab-branch-validation-fail",
            ["client1", "client2", "srl1", "srl2"],
        ),
    }

    result = validate_session(session)
    failed_ids = {check.check_id for check in result.checks if not check.passed}

    assert result.passed is False
    assert result.score < 100
    assert "branch_check_4_client2_default_gateway" in failed_ids


def test_checkpoint2_edge_and_campus_canonical_ids_use_live_validation_paths(monkeypatch):
    def fake_edge_run(command, **kwargs):
        command_text = " ".join(str(part) for part in command)

        if "ip -4 addr show dev eth1" in command_text:
            return FakeCompletedProcess(stdout="inet 10.10.10.10/24 scope global eth1\n")

        if "ip route" in command_text:
            return FakeCompletedProcess(stdout="default via 10.10.10.1 dev eth1\n")

        if "info from state interface ethernet-1/1 subinterface 0 ipv4" in command_text:
            return FakeCompletedProcess(stdout="address 10.10.10.1/24 {\n}\n")

        if "info network-instance default" in command_text:
            return FakeCompletedProcess(stdout="interface ethernet-1/1.0 {\n}\n")

        if "ping" in command_text and "10.10.10.1" in command_text:
            return FakeCompletedProcess(stdout="64 bytes from 10.10.10.1: icmp_seq=1 ttl=64 time=1 ms\n")

        return FakeCompletedProcess()

    monkeypatch.setattr(
        "app.services.validation_service.subprocess.run",
        fake_edge_run,
    )

    edge_session = {
        "session_id": "lab-edge-validation-pass",
        "status": SessionStatus.deployed,
        "scenario": {"id": SR_EDGE_LINK_SCENARIO_ID},
        "topology_template": SR_EDGE_LINK_SCENARIO_ID,
        "cli_access": _cli_access("lab-edge-validation-pass", ["client1", "srl1"]),
    }

    edge_result = validate_session(edge_session)

    assert edge_result.passed is True
    assert edge_result.score == 100
    assert len(edge_result.checks) == 5

    legacy_edge_session = {
        **edge_session,
        "scenario": {"id": SR_BASIC_LINK_SCENARIO_ID},
        "topology_template": SR_BASIC_LINK_SCENARIO_ID,
    }

    legacy_edge_result = validate_session(legacy_edge_session)

    assert legacy_edge_result.passed is True
    assert legacy_edge_result.score == 100
    assert len(legacy_edge_result.checks) == 5
