from app.schemas.enums import SessionStatus
from app.schemas.validation import StudentValidationResult
from app.services.scenario_catalog import (
    CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID,
    SR_BASIC_LINK_SCENARIO_ID,
)
from app.services.validation_service import validate_session


def _cli_access(devices: list[str], session_id: str = "lab-live-validation-test") -> list[dict[str, str]]:
    return [
        {
            "device_id": device,
            "name": device,
            "container_name": f"clab-autonetlab-{session_id}-{device}",
        }
        for device in devices
    ]


def _campus_session(status=SessionStatus.deployed) -> dict:
    session_id = "lab-campus-live-validation-test"
    return {
        "session_id": session_id,
        "status": status,
        "scenario": {"id": CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID},
        "topology_template": CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID,
        "cli_access": _cli_access(
            ["client1", "client2", "srl1", "srl2", "srl3", "srl4"],
            session_id=session_id,
        ),
    }


def _basic_link_session() -> dict:
    session_id = "lab-basic-link-live-validation-test"
    return {
        "session_id": session_id,
        "status": SessionStatus.deployed,
        "scenario": {"id": SR_BASIC_LINK_SCENARIO_ID},
        "topology_template": SR_BASIC_LINK_SCENARIO_ID,
        "cli_access": _cli_access(["client1", "srl1"], session_id=session_id),
    }


class FakeCompletedProcess:
    def __init__(self, stdout: str = "", stderr: str = "", returncode: int = 0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def _fake_campus_golden_run(command, **_kwargs):
    command_text = " ".join(str(part) for part in command)

    if "client1" in command_text and "ip -4 addr show dev eth1" in command_text:
        return FakeCompletedProcess(stdout="inet 10.10.10.10/24 scope global eth1\n")

    if "client2" in command_text and "ip -4 addr show dev eth1" in command_text:
        return FakeCompletedProcess(stdout="inet 10.10.20.10/24 scope global eth1\n")

    if "client1" in command_text and command_text.endswith(" ip route"):
        return FakeCompletedProcess(stdout="default via 10.10.10.1 dev eth1\n")

    if "client2" in command_text and command_text.endswith(" ip route"):
        return FakeCompletedProcess(stdout="default via 10.10.20.1 dev eth1\n")

    if "client1" in command_text and "ping" in command_text and "10.10.20.10" in command_text:
        return FakeCompletedProcess(stdout="64 bytes from 10.10.20.10: icmp_seq=1 ttl=62 time=4.1 ms\n")

    if "client2" in command_text and "ping" in command_text and "10.10.10.10" in command_text:
        return FakeCompletedProcess(stdout="64 bytes from 10.10.10.10: icmp_seq=1 ttl=62 time=4.1 ms\n")

    if "srl1" in command_text and "info from state interface" in command_text:
        return FakeCompletedProcess(
            stdout=(
                "address 10.10.10.1/24 {\n}\n"
                "address 10.10.13.1/30 {\n}\n"
                "address 10.10.14.1/30 {\n}\n"
            )
        )

    if "srl2" in command_text and "info from state interface" in command_text:
        return FakeCompletedProcess(
            stdout=(
                "address 10.10.20.1/24 {\n}\n"
                "address 10.10.23.1/30 {\n}\n"
                "address 10.10.24.1/30 {\n}\n"
            )
        )

    if "srl3" in command_text and "info network-instance default static-routes" in command_text:
        return FakeCompletedProcess(
            stdout=(
                "static-next-hop-group campus-srl3-to-client1\n"
                "static-next-hop-group campus-srl3-to-client2\n"
            )
        )

    if "srl1" in command_text and "info network-instance default static-routes route 10.10.20.0/24" in command_text:
        return FakeCompletedProcess(stdout="static-next-hop-group campus-srl1-to-client2\n")

    if "srl2" in command_text and "info network-instance default static-routes route 10.10.10.0/24" in command_text:
        return FakeCompletedProcess(stdout="static-next-hop-group campus-srl2-to-client1\n")

    return FakeCompletedProcess(stdout="")


def test_nr_sprint34a_campus_golden_live_validation_passes(monkeypatch):
    monkeypatch.setattr(
        "app.services.validation_service.subprocess.run",
        _fake_campus_golden_run,
    )

    result = validate_session(_campus_session())

    assert result.passed is True
    assert result.score == 100
    assert len(result.checks) == 11
    assert {check.status for check in result.checks} == {"passed"}
    assert [check.check_id for check in result.checks] == [
        "campus_check_1_client1_address",
        "campus_check_2_client1_default_gateway",
        "campus_check_3_client2_address",
        "campus_check_4_client2_default_gateway",
        "campus_check_5_client1_to_client2_connectivity",
        "campus_check_6_client2_to_client1_connectivity",
        "campus_check_7_srl1_edge_and_core_interfaces",
        "campus_check_8_srl2_edge_and_core_interfaces",
        "campus_check_9_srl3_transit_routes",
        "campus_check_10_srl1_route_to_client2",
        "campus_check_11_srl2_route_to_client1",
    ]

    assert all(check.evidence for check in result.checks)

    student_result = StudentValidationResult(**result.model_dump(mode="json"))
    student_payload = student_result.model_dump(mode="json")

    assert "evidence" not in str(student_payload)
    assert "injected_errors" not in str(student_payload)
    assert "10.10.10.254" not in str(student_payload)


def test_nr_sprint34a_campus_live_validation_detects_failed_client_gateway(monkeypatch):
    def fake_run(command, **kwargs):
        command_text = " ".join(str(part) for part in command)

        if "client2" in command_text and command_text.endswith(" ip route"):
            return FakeCompletedProcess(stdout="default via 10.10.20.254 dev eth1\n")

        return _fake_campus_golden_run(command, **kwargs)

    monkeypatch.setattr(
        "app.services.validation_service.subprocess.run",
        fake_run,
    )

    result = validate_session(_campus_session())

    failed_checks = [check for check in result.checks if not check.passed]

    assert result.passed is False
    assert result.score < 100
    assert [check.check_id for check in failed_checks] == [
        "campus_check_4_client2_default_gateway",
    ]

    student_result = StudentValidationResult(**result.model_dump(mode="json"))
    assert "evidence" not in str(student_result.model_dump(mode="json"))


def test_nr_sprint34a_campus_validation_requires_deployed_runtime():
    result = validate_session(_campus_session(status=SessionStatus.created))

    assert result.passed is False
    assert result.score == 0
    assert len(result.checks) == 1
    assert result.checks[0].check_id == "campus_check_runtime_deployed"
    assert "runtime is not deployed" in result.checks[0].message


def test_nr_sprint34a_srl_basic_link_validation_still_uses_basic_path(monkeypatch):
    def fake_run(command, **_kwargs):
        command_text = " ".join(str(part) for part in command)

        if "srl1" in command_text and "info from state interface ethernet-1/1" in command_text:
            return FakeCompletedProcess(stdout="address 10.10.10.1/24 {\n}\n")

        if "srl1" in command_text and "info network-instance default" in command_text:
            return FakeCompletedProcess(stdout="interface ethernet-1/1.0 {\n}\n")

        if "client1" in command_text and "ip -4 addr show dev eth1" in command_text:
            return FakeCompletedProcess(stdout="inet 10.10.10.10/24 scope global eth1\n")

        if "client1" in command_text and command_text.endswith(" ip route"):
            return FakeCompletedProcess(stdout="default via 10.10.10.1 dev eth1\n")

        if "client1" in command_text and "ping" in command_text and "10.10.10.1" in command_text:
            return FakeCompletedProcess(stdout="64 bytes from 10.10.10.1: icmp_seq=1 ttl=64 time=1.1 ms\n")

        return FakeCompletedProcess(stdout="")

    monkeypatch.setattr(
        "app.services.validation_service.subprocess.run",
        fake_run,
    )

    result = validate_session(_basic_link_session())

    assert result.passed is True
    assert result.score == 100
    assert len(result.checks) == 5
    assert [check.check_id for check in result.checks] == [
        "srl_check_1_router_gateway_address",
        "srl_check_2_router_network_instance",
        "srl_check_3_client_address",
        "srl_check_4_client_default_gateway",
        "srl_check_5_gateway_connectivity",
    ]
