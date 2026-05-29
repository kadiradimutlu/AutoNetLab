from copy import deepcopy

from fastapi import HTTPException, status


SR_LINUX_IMAGE = "ghcr.io/nokia/srlinux:26.3.2"
NETWORK_CLIENT_IMAGE = "ghcr.io/srl-labs/network-multitool:latest"

SR_BASIC_LINK_SCENARIO_ID = "srl-basic-link"


_SCENARIOS: dict[str, dict] = {
    SR_BASIC_LINK_SCENARIO_ID: {
        "id": SR_BASIC_LINK_SCENARIO_ID,
        "title": "SR Linux Basic Link Troubleshooting",
        "summary": "A professional router-client starter scenario using Nokia SR Linux and a Linux client.",
        "topology_template": "srl-basic-link",
        "platform": "containerlab",
        "router_os": "Nokia SR Linux",
        "supported_difficulties": ["easy", "medium", "hard"],
        "objective": "Restore the expected connectivity between client1 and the SR Linux router.",
        "story": (
            "A small routed edge segment is being prepared for network troubleshooting practice. "
            "Use the design requirements below as the source of truth while inspecting the live lab."
        ),
        "devices": [
            {
                "id": "srl1",
                "label": "SR Linux Router 1",
                "role": "router",
                "os": "Nokia SR Linux",
                "image": SR_LINUX_IMAGE,
                "cli_profile": "sr_cli",
            },
            {
                "id": "client1",
                "label": "Client 1",
                "role": "client",
                "os": "Linux",
                "image": NETWORK_CLIENT_IMAGE,
                "cli_profile": "linux_shell",
            },
        ],
        "addressing_table": [
            {
                "device": "srl1",
                "interface": "ethernet-1/1",
                "ip_address": "10.10.10.1/24",
                "role": "default gateway for client1",
                "connects_to": "client1 eth1",
            },
            {
                "device": "client1",
                "interface": "eth1",
                "ip_address": "10.10.10.10/24",
                "default_gateway": "10.10.10.1",
                "connects_to": "srl1 ethernet-1/1",
            },
        ],
        "routing_requirements": [
            {
                "device": "client1",
                "requirement": "client1 must use 10.10.10.1 as its default gateway.",
            },
            {
                "device": "srl1",
                "requirement": "srl1 ethernet-1/1 must be configured in the 10.10.10.0/24 client subnet.",
            },
        ],
        "expected_connectivity": [
            {
                "source": "client1",
                "destination": "10.10.10.1",
                "protocol": "ICMP",
                "expectation": "client1 can ping the SR Linux router gateway.",
            }
        ],
        "student_tasks": [
            "Inspect the topology and identify the router and client roles.",
            "Compare the live device state with the addressing table.",
            "Verify the client default gateway.",
            "Restore the expected connectivity and run validation.",
        ],
        "student_notes": [
            "Injected faults are hidden from the student view.",
            "Use the scenario design requirements as the expected network state.",
        ],
    }
}


def list_scenarios() -> list[dict]:
    return [deepcopy(scenario) for scenario in _SCENARIOS.values()]


def get_scenario(scenario_id: str | None) -> dict | None:
    if not scenario_id:
        return None

    scenario = _SCENARIOS.get(scenario_id)

    if scenario is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported scenario_id: {scenario_id}",
        )

    return deepcopy(scenario)


def is_srlinux_scenario(scenario_id: str | None) -> bool:
    return scenario_id == SR_BASIC_LINK_SCENARIO_ID
