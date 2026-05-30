from app.schemas.enums import SessionStatus
from app.services.scenario_catalog import (
    CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID,
    get_scenario,
    is_srlinux_scenario,
)


def _campus_cli_access(session_id: str = "lab-campus-golden-test") -> list[dict[str, str]]:
    return [
        {
            "device_id": device,
            "name": device,
            "container_name": f"clab-autonetlab-{session_id}-{device}",
        }
        for device in ["client1", "client2", "srl1", "srl2", "srl3", "srl4"]
    ]


def test_nr_sprint33a_catalog_exposes_campus_golden_static_routing_metadata():
    scenario = get_scenario(CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID)

    assert scenario["runtime_profile"] == "deploy_only"
    assert is_srlinux_scenario(CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID) is True

    static_routes = {
        (item["device"], item["destination"]): item["next_hop"]
        for item in scenario["static_routing_table"]
    }

    assert static_routes[("srl1", "10.10.20.0/24")] == "10.10.13.2"
    assert static_routes[("srl2", "10.10.10.0/24")] == "10.10.23.2"
    assert static_routes[("srl3", "10.10.10.0/24")] == "10.10.13.1"
    assert static_routes[("srl3", "10.10.20.0/24")] == "10.10.23.1"
    assert static_routes[("srl4", "10.10.10.0/24")] == "10.10.14.1"
    assert static_routes[("srl4", "10.10.20.0/24")] == "10.10.24.1"

    expectations = {
        item["destination"]: item["expectation"]
        for item in scenario["expected_connectivity"]
    }
    assert "client1 can ping client2" in expectations["10.10.20.10"]
    assert "client2 can ping client1" in expectations["10.10.10.10"]


def test_nr_sprint33a_campus_runtime_setup_applies_golden_state(monkeypatch):
    from app.services.srlinux_runtime_setup import apply_srlinux_runtime_setup

    session_id = "lab-campus-golden-test"
    session = {
        "session_id": session_id,
        "scenario": {"id": CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID},
        "injected_errors": [],
        "cli_access": _campus_cli_access(session_id),
    }

    executed_commands = []
    sr_cli_inputs = []

    class FakeCompletedProcess:
        def __init__(self, stdout: str = "ok\n", returncode: int = 0):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = ""

    def fake_run(command, **kwargs):
        command_text = " ".join(command)
        executed_commands.append(command_text)

        if kwargs.get("input"):
            sr_cli_inputs.append(kwargs["input"])

        if "ip -4 addr show dev eth1" in command_text and "client1" in command_text:
            return FakeCompletedProcess(stdout="inet 10.10.10.10/24 scope global eth1\n")

        if "ip -4 addr show dev eth1" in command_text and "client2" in command_text:
            return FakeCompletedProcess(stdout="inet 10.10.20.10/24 scope global eth1\n")

        if command_text.endswith(" ip route") and "client1" in command_text:
            return FakeCompletedProcess(stdout="default via 10.10.10.1 dev eth1\n")

        if command_text.endswith(" ip route") and "client2" in command_text:
            return FakeCompletedProcess(stdout="default via 10.10.20.1 dev eth1\n")

        if "info from state interface" in command_text:
            interface_outputs = {
                "ethernet-1/1": "10.10.10.1/24",
                "ethernet-1/2": "10.10.13.1/30",
                "ethernet-1/3": "10.10.14.1/30",
            }

            if "srl2" in command_text:
                interface_outputs = {
                    "ethernet-1/1": "10.10.20.1/24",
                    "ethernet-1/2": "10.10.23.1/30",
                    "ethernet-1/3": "10.10.24.1/30",
                }
            elif "srl3" in command_text:
                interface_outputs = {
                    "ethernet-1/1": "10.10.13.2/30",
                    "ethernet-1/2": "10.10.23.2/30",
                }
            elif "srl4" in command_text:
                interface_outputs = {
                    "ethernet-1/1": "10.10.14.2/30",
                    "ethernet-1/2": "10.10.24.2/30",
                }

            for interface, address in interface_outputs.items():
                if interface in command_text:
                    return FakeCompletedProcess(stdout=f"address {address} {{\n}}\n")

        if "info network-instance default static-routes route" in command_text:
            prefix = command_text.split("route ", maxsplit=1)[1]
            return FakeCompletedProcess(stdout=f"route {prefix} {{\n    admin-state enable\n}}\n")

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

    monkeypatch.setattr(
        "app.services.srlinux_runtime_setup.subprocess.run",
        fake_run,
    )

    result = apply_srlinux_runtime_setup(session)

    assert result["success"] is True
    assert result["status"] == SessionStatus.deployed
    assert result["message"] == "SR Linux campus golden runtime setup applied successfully."

    joined_commands = "\n".join(executed_commands)
    joined_sr_cli_inputs = "\n".join(sr_cli_inputs)

    assert "ip addr add 10.10.10.10/24 dev eth1" in joined_commands
    assert "ip route replace default via 10.10.10.1 dev eth1" in joined_commands
    assert "ip addr add 10.10.20.10/24 dev eth1" in joined_commands
    assert "ip route replace default via 10.10.20.1 dev eth1" in joined_commands

    assert "set interface ethernet-1/2 subinterface 0 ipv4 address 10.10.13.1/30" in joined_sr_cli_inputs
    assert "set network-instance default interface ethernet-1/2.0" in joined_sr_cli_inputs
    assert "set network-instance default static next-hop 1 ip-address 10.10.13.2" in joined_sr_cli_inputs
    assert "set network-instance default static-routes route 10.10.20.0/24 static-next-hop-group campus-srl1-to-client2" in joined_sr_cli_inputs
    assert "set network-instance default static-routes route 10.10.10.0/24 static-next-hop-group campus-srl2-to-client1" in joined_sr_cli_inputs
    assert "set network-instance default static-routes route 10.10.20.0/24 static-next-hop-group campus-srl4-to-client2" in joined_sr_cli_inputs

    assert "10.10.10.254" not in joined_commands
    assert "10.10.10.254" not in joined_sr_cli_inputs
