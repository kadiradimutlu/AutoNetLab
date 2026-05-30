from copy import deepcopy

from fastapi import HTTPException, status


SR_LINUX_IMAGE = "ghcr.io/nokia/srlinux:26.3.2"
NETWORK_CLIENT_IMAGE = "ghcr.io/srl-labs/network-multitool:latest"

SR_BASIC_LINK_SCENARIO_ID = "srl-basic-link"
CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID = "campus-core-static-routing"

DEPLOY_ONLY_SCENARIO_IDS = {
    CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID,
}


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
    },
    CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID: {
        "id": CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID,
        "title": "Campus Core Static Routing",
        "summary": (
            "A professional campus-core foundation scenario with two Linux clients "
            "and four Nokia SR Linux routers."
        ),
        "topology_template": "campus-core-static-routing",
        "platform": "containerlab",
        "router_os": "Nokia SR Linux",
        "supported_difficulties": ["easy", "medium", "hard"],
        "objective": (
            "Deploy a golden campus static-routing baseline with end-to-end "
            "client connectivity across the SR Linux core."
        ),
        "story": (
            "A campus network has two client edge segments connected through a four-router "
            "SR Linux core. The golden baseline configures client addressing, SR Linux "
            "routed subinterfaces, network-instance bindings, and static routes."
        ),
        "runtime_profile": "deploy_only",
        "devices": [
            {
                "id": "client1",
                "label": "Client 1",
                "role": "client",
                "os": "Linux",
                "image": NETWORK_CLIENT_IMAGE,
                "cli_profile": "linux_shell",
            },
            {
                "id": "client2",
                "label": "Client 2",
                "role": "client",
                "os": "Linux",
                "image": NETWORK_CLIENT_IMAGE,
                "cli_profile": "linux_shell",
            },
            {
                "id": "srl1",
                "label": "Campus Edge Router 1",
                "role": "edge_router",
                "os": "Nokia SR Linux",
                "image": SR_LINUX_IMAGE,
                "cli_profile": "sr_cli",
            },
            {
                "id": "srl2",
                "label": "Campus Edge Router 2",
                "role": "edge_router",
                "os": "Nokia SR Linux",
                "image": SR_LINUX_IMAGE,
                "cli_profile": "sr_cli",
            },
            {
                "id": "srl3",
                "label": "Campus Core Router 3",
                "role": "core_router",
                "os": "Nokia SR Linux",
                "image": SR_LINUX_IMAGE,
                "cli_profile": "sr_cli",
            },
            {
                "id": "srl4",
                "label": "Campus Core Router 4",
                "role": "core_router",
                "os": "Nokia SR Linux",
                "image": SR_LINUX_IMAGE,
                "cli_profile": "sr_cli",
            },
        ],
        "links": [
            {
                "source": {"node": "client1", "interface": "eth1"},
                "target": {"node": "srl1", "interface": "ethernet-1/1"},
                "subnet": "10.10.10.0/24",
            },
            {
                "source": {"node": "srl1", "interface": "ethernet-1/2"},
                "target": {"node": "srl3", "interface": "ethernet-1/1"},
                "subnet": "10.10.13.0/30",
            },
            {
                "source": {"node": "srl3", "interface": "ethernet-1/2"},
                "target": {"node": "srl2", "interface": "ethernet-1/2"},
                "subnet": "10.10.23.0/30",
            },
            {
                "source": {"node": "srl2", "interface": "ethernet-1/1"},
                "target": {"node": "client2", "interface": "eth1"},
                "subnet": "10.10.20.0/24",
            },
            {
                "source": {"node": "srl1", "interface": "ethernet-1/3"},
                "target": {"node": "srl4", "interface": "ethernet-1/1"},
                "subnet": "10.10.14.0/30",
            },
            {
                "source": {"node": "srl4", "interface": "ethernet-1/2"},
                "target": {"node": "srl2", "interface": "ethernet-1/3"},
                "subnet": "10.10.24.0/30",
            },
        ],
        "addressing_table": [
            {
                "device": "client1",
                "interface": "eth1",
                "ip_address": "10.10.10.10/24",
                "default_gateway": "10.10.10.1",
                "connects_to": "srl1 ethernet-1/1",
            },
            {
                "device": "srl1",
                "interface": "ethernet-1/1",
                "ip_address": "10.10.10.1/24",
                "connects_to": "client1 eth1",
            },
            {
                "device": "srl1",
                "interface": "ethernet-1/2",
                "ip_address": "10.10.13.1/30",
                "connects_to": "srl3 ethernet-1/1",
            },
            {
                "device": "srl3",
                "interface": "ethernet-1/1",
                "ip_address": "10.10.13.2/30",
                "connects_to": "srl1 ethernet-1/2",
            },
            {
                "device": "srl3",
                "interface": "ethernet-1/2",
                "ip_address": "10.10.23.2/30",
                "connects_to": "srl2 ethernet-1/2",
            },
            {
                "device": "srl2",
                "interface": "ethernet-1/2",
                "ip_address": "10.10.23.1/30",
                "connects_to": "srl3 ethernet-1/2",
            },
            {
                "device": "srl1",
                "interface": "ethernet-1/3",
                "ip_address": "10.10.14.1/30",
                "connects_to": "srl4 ethernet-1/1",
            },
            {
                "device": "srl4",
                "interface": "ethernet-1/1",
                "ip_address": "10.10.14.2/30",
                "connects_to": "srl1 ethernet-1/3",
            },
            {
                "device": "srl4",
                "interface": "ethernet-1/2",
                "ip_address": "10.10.24.2/30",
                "connects_to": "srl2 ethernet-1/3",
            },
            {
                "device": "srl2",
                "interface": "ethernet-1/3",
                "ip_address": "10.10.24.1/30",
                "connects_to": "srl4 ethernet-1/2",
            },
            {
                "device": "srl2",
                "interface": "ethernet-1/1",
                "ip_address": "10.10.20.1/24",
                "connects_to": "client2 eth1",
            },
            {
                "device": "client2",
                "interface": "eth1",
                "ip_address": "10.10.20.10/24",
                "default_gateway": "10.10.20.1",
                "connects_to": "srl2 ethernet-1/1",
            },
        ],
        "routing_requirements": [
            {
                "device": "client1",
                "requirement": "client1 should use 10.10.10.1 as its default gateway.",
            },
            {
                "device": "client2",
                "requirement": "client2 should use 10.10.20.1 as its default gateway.",
            },
            {
                "device": "srl1",
                "requirement": "srl1 should route toward client2 through the SR Linux core.",
            },
            {
                "device": "srl2",
                "requirement": "srl2 should route toward client1 through the SR Linux core.",
            },
            {
                "device": "srl3",
                "requirement": "srl3 is the upper core transit router between srl1 and srl2.",
            },
            {
                "device": "srl4",
                "requirement": "srl4 is the lower core transit router between srl1 and srl2.",
            },
        ],
        "static_routing_table": [
            {
                "device": "srl1",
                "destination": "10.10.20.0/24",
                "next_hop": "10.10.13.2",
                "path": "primary path toward client2 via srl3",
            },
            {
                "device": "srl2",
                "destination": "10.10.10.0/24",
                "next_hop": "10.10.23.2",
                "path": "primary path toward client1 via srl3",
            },
            {
                "device": "srl3",
                "destination": "10.10.10.0/24",
                "next_hop": "10.10.13.1",
                "path": "return path toward client1 edge",
            },
            {
                "device": "srl3",
                "destination": "10.10.20.0/24",
                "next_hop": "10.10.23.1",
                "path": "forward path toward client2 edge",
            },
            {
                "device": "srl4",
                "destination": "10.10.10.0/24",
                "next_hop": "10.10.14.1",
                "path": "alternate lower-core path toward client1 edge",
            },
            {
                "device": "srl4",
                "destination": "10.10.20.0/24",
                "next_hop": "10.10.24.1",
                "path": "alternate lower-core path toward client2 edge",
            },
        ],
        "expected_connectivity": [
            {
                "source": "client1",
                "destination": "10.10.20.10",
                "protocol": "ICMP",
                "expectation": "client1 can ping client2 across the campus core.",
            },
            {
                "source": "client2",
                "destination": "10.10.10.10",
                "protocol": "ICMP",
                "expectation": "client2 can ping client1 across the campus core.",
            },
        ],
        "student_tasks": [
            "Inspect all six nodes and their roles.",
            "Review the campus addressing table.",
            "Understand the redundant SR Linux core paths.",
            "Use this topology as the base for future routing and validation sprints.",
        ],
        "student_notes": [
            "This scenario starts from a golden campus static-routing baseline.",
            "Runtime fault injection and full routing validation are planned for later sprints.",
            "No hidden solution data is exposed in the student response.",
        ],
    },
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
    return scenario_id in {
        SR_BASIC_LINK_SCENARIO_ID,
        CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID,
    }


def is_deploy_only_scenario(scenario_id: str | None) -> bool:
    return scenario_id in DEPLOY_ONLY_SCENARIO_IDS
