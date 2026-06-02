from copy import deepcopy

from fastapi import HTTPException, status


SR_LINUX_IMAGE = "ghcr.io/nokia/srlinux:26.3.2"
NETWORK_CLIENT_IMAGE = "ghcr.io/srl-labs/network-multitool:latest"

SR_EDGE_LINK_SCENARIO_ID = "srl-edge-link"
BRANCH_STATIC_ROUTING_SCENARIO_ID = "branch-static-routing"
CAMPUS_CORE_ROUTING_SCENARIO_ID = "campus-core-routing"

# Legacy identifiers are accepted for backward compatibility, but they are not
# exposed by the student-facing scenario catalog.
SR_BASIC_LINK_SCENARIO_ID = "srl-basic-link"
CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID = "campus-core-static-routing"

DEFAULT_SCENARIO_ID = SR_EDGE_LINK_SCENARIO_ID

SCENARIO_ALIASES: dict[str, str] = {
    SR_BASIC_LINK_SCENARIO_ID: SR_EDGE_LINK_SCENARIO_ID,
    CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID: CAMPUS_CORE_ROUTING_SCENARIO_ID,
}

DEPLOY_ONLY_SCENARIO_IDS: set[str] = set()

DIFFICULTY_FAULT_COUNTS: dict[str, int] = {
    "easy": 1,
    "medium": 2,
    "hard": 3,
}

SUPPORTED_DIFFICULTIES = list(DIFFICULTY_FAULT_COUNTS.keys())


def _scenario_base(
    *,
    scenario_id: str,
    title: str,
    summary: str,
    objective: str,
    story: str,
    topology_template: str,
    topology_metadata: dict,
    devices: list[dict],
    links: list[dict],
    addressing_table: list[dict],
    interface_requirements: list[dict],
    routing_requirements: list[dict],
    expected_connectivity: list[dict],
    student_tasks: list[str],
    static_routing_table: list[dict] | None = None,
) -> dict:
    expected_network_state = {
        "addressing_table": deepcopy(addressing_table),
        "interface_requirements": deepcopy(interface_requirements),
        "routing_requirements": deepcopy(routing_requirements),
        "expected_connectivity": deepcopy(expected_connectivity),
    }

    if static_routing_table is not None:
        expected_network_state["static_routing_table"] = deepcopy(static_routing_table)

    return {
        "id": scenario_id,
        "title": title,
        "summary": summary,
        "topology_template": topology_template,
        "platform": "containerlab",
        "router_os": "Nokia SR Linux",
        "runtime_profile": "runtime_fault_injection",
        "supported_difficulties": SUPPORTED_DIFFICULTIES,
        "difficulty_fault_counts": deepcopy(DIFFICULTY_FAULT_COUNTS),
        "objective": objective,
        "story": story,
        "topology_metadata": deepcopy(topology_metadata),
        "devices": devices,
        "links": links,
        "addressing_table": addressing_table,
        "interface_requirements": interface_requirements,
        "routing_requirements": routing_requirements,
        "expected_connectivity": expected_connectivity,
        "expected_network_state": expected_network_state,
        "student_tasks": student_tasks,
        "student_notes": [
            "Injected faults are hidden from the student view.",
            "Use the scenario design requirements as the expected network state.",
            "Validation checks the expected training design, not an arbitrary alternative IP plan.",
        ],
    }


_SCENARIOS: dict[str, dict] = {
    SR_EDGE_LINK_SCENARIO_ID: _scenario_base(
        scenario_id=SR_EDGE_LINK_SCENARIO_ID,
        title="Edge Link Troubleshooting",
        summary="Troubleshoot a single edge router link between one Linux client and one Nokia SR Linux router.",
        topology_template=SR_EDGE_LINK_SCENARIO_ID,
        objective="Restore the expected edge connectivity between client1 and the SR Linux default gateway.",
        story=(
            "A branch edge segment is down after a configuration change. "
            "Use the expected addressing and interface requirements to restore connectivity."
        ),
        topology_metadata={
            "topology_type": "edge_link",
            "device_count": 2,
            "router_count": 1,
            "client_count": 1,
            "link_count": 1,
            "devices": ["client1", "srl1"],
        },
        devices=[
            {"id": "client1", "label": "Client 1", "role": "client", "os": "Linux", "image": NETWORK_CLIENT_IMAGE, "cli_profile": "linux_shell"},
            {"id": "srl1", "label": "Edge Router", "role": "edge_router", "os": "Nokia SR Linux", "image": SR_LINUX_IMAGE, "cli_profile": "sr_cli"},
        ],
        links=[
            {"source": {"node": "client1", "interface": "eth1"}, "target": {"node": "srl1", "interface": "ethernet-1/1"}, "subnet": "10.10.10.0/24"},
        ],
        addressing_table=[
            {"device": "client1", "interface": "eth1", "ip_address": "10.10.10.10/24", "default_gateway": "10.10.10.1", "connects_to": "srl1 ethernet-1/1"},
            {"device": "srl1", "interface": "ethernet-1/1", "ip_address": "10.10.10.1/24", "network_instance": "default", "connects_to": "client1 eth1"},
        ],
        interface_requirements=[
            {"device": "client1", "interface": "eth1", "required_state": "up", "required_ip": "10.10.10.10/24"},
            {"device": "srl1", "interface": "ethernet-1/1.0", "required_state": "up", "required_ip": "10.10.10.1/24", "network_instance": "default"},
        ],
        routing_requirements=[
            {"device": "client1", "requirement": "client1 must use 10.10.10.1 as its default gateway."},
            {"device": "srl1", "requirement": "srl1 ethernet-1/1.0 must be attached to the default network-instance."},
        ],
        expected_connectivity=[
            {"source": "client1", "destination": "10.10.10.1", "protocol": "ICMP", "expectation": "client1 can ping the SR Linux gateway."},
        ],
        student_tasks=[
            "Inspect the edge link topology.",
            "Compare client1 and srl1 live state with the expected addressing table.",
            "Verify the client default gateway and SR Linux interface state.",
            "Restore the expected network state and run validation.",
        ],
    ),
    BRANCH_STATIC_ROUTING_SCENARIO_ID: _scenario_base(
        scenario_id=BRANCH_STATIC_ROUTING_SCENARIO_ID,
        title="Branch Static Routing",
        summary="Troubleshoot static routing between two branch clients through two Nokia SR Linux routers.",
        topology_template=BRANCH_STATIC_ROUTING_SCENARIO_ID,
        objective="Restore end-to-end connectivity between client1 and client2 across the two-router branch path.",
        story=(
            "Two branch LANs are connected through a pair of SR Linux routers. "
            "Students must verify addressing, gateway, interface, and static-route requirements."
        ),
        topology_metadata={
            "topology_type": "branch_static_routing",
            "device_count": 4,
            "router_count": 2,
            "client_count": 2,
            "link_count": 3,
            "devices": ["client1", "srl1", "srl2", "client2"],
        },
        devices=[
            {"id": "client1", "label": "Branch Client 1", "role": "client", "os": "Linux", "image": NETWORK_CLIENT_IMAGE, "cli_profile": "linux_shell"},
            {"id": "srl1", "label": "Branch Router 1", "role": "edge_router", "os": "Nokia SR Linux", "image": SR_LINUX_IMAGE, "cli_profile": "sr_cli"},
            {"id": "srl2", "label": "Branch Router 2", "role": "edge_router", "os": "Nokia SR Linux", "image": SR_LINUX_IMAGE, "cli_profile": "sr_cli"},
            {"id": "client2", "label": "Branch Client 2", "role": "client", "os": "Linux", "image": NETWORK_CLIENT_IMAGE, "cli_profile": "linux_shell"},
        ],
        links=[
            {"source": {"node": "client1", "interface": "eth1"}, "target": {"node": "srl1", "interface": "ethernet-1/1"}, "subnet": "10.10.10.0/24"},
            {"source": {"node": "srl1", "interface": "ethernet-1/2"}, "target": {"node": "srl2", "interface": "ethernet-1/2"}, "subnet": "10.10.12.0/30"},
            {"source": {"node": "srl2", "interface": "ethernet-1/1"}, "target": {"node": "client2", "interface": "eth1"}, "subnet": "10.10.20.0/24"},
        ],
        addressing_table=[
            {"device": "client1", "interface": "eth1", "ip_address": "10.10.10.10/24", "default_gateway": "10.10.10.1", "connects_to": "srl1 ethernet-1/1"},
            {"device": "srl1", "interface": "ethernet-1/1", "ip_address": "10.10.10.1/24", "connects_to": "client1 eth1"},
            {"device": "srl1", "interface": "ethernet-1/2", "ip_address": "10.10.12.1/30", "connects_to": "srl2 ethernet-1/2"},
            {"device": "srl2", "interface": "ethernet-1/2", "ip_address": "10.10.12.2/30", "connects_to": "srl1 ethernet-1/2"},
            {"device": "srl2", "interface": "ethernet-1/1", "ip_address": "10.10.20.1/24", "connects_to": "client2 eth1"},
            {"device": "client2", "interface": "eth1", "ip_address": "10.10.20.10/24", "default_gateway": "10.10.20.1", "connects_to": "srl2 ethernet-1/1"},
        ],
        interface_requirements=[
            {"device": "client1", "interface": "eth1", "required_state": "up", "required_ip": "10.10.10.10/24"},
            {"device": "client2", "interface": "eth1", "required_state": "up", "required_ip": "10.10.20.10/24"},
            {"device": "srl1", "interface": "ethernet-1/1.0", "required_state": "up", "required_ip": "10.10.10.1/24", "network_instance": "default"},
            {"device": "srl1", "interface": "ethernet-1/2.0", "required_state": "up", "required_ip": "10.10.12.1/30", "network_instance": "default"},
            {"device": "srl2", "interface": "ethernet-1/1.0", "required_state": "up", "required_ip": "10.10.20.1/24", "network_instance": "default"},
            {"device": "srl2", "interface": "ethernet-1/2.0", "required_state": "up", "required_ip": "10.10.12.2/30", "network_instance": "default"},
        ],
        routing_requirements=[
            {"device": "client1", "requirement": "client1 should use 10.10.10.1 as its default gateway."},
            {"device": "client2", "requirement": "client2 should use 10.10.20.1 as its default gateway."},
            {"device": "srl1", "requirement": "srl1 should route 10.10.20.0/24 via 10.10.12.2."},
            {"device": "srl2", "requirement": "srl2 should route 10.10.10.0/24 via 10.10.12.1."},
        ],
        static_routing_table=[
            {"device": "srl1", "destination": "10.10.20.0/24", "next_hop": "10.10.12.2", "path": "toward client2 through srl2"},
            {"device": "srl2", "destination": "10.10.10.0/24", "next_hop": "10.10.12.1", "path": "toward client1 through srl1"},
        ],
        expected_connectivity=[
            {"source": "client1", "destination": "10.10.20.10", "protocol": "ICMP", "expectation": "client1 can ping client2 through the branch routers."},
            {"source": "client2", "destination": "10.10.10.10", "protocol": "ICMP", "expectation": "client2 can ping client1 through the branch routers."},
        ],
        student_tasks=[
            "Inspect both branch clients and both SR Linux routers.",
            "Verify client gateways and SR Linux interface addressing.",
            "Review the static routes between the two client LANs.",
            "Restore end-to-end connectivity and run validation.",
        ],
    ),
    CAMPUS_CORE_ROUTING_SCENARIO_ID: _scenario_base(
        scenario_id=CAMPUS_CORE_ROUTING_SCENARIO_ID,
        title="Campus Core Troubleshooting",
        summary="Troubleshoot a six-node campus core with two Linux clients and four Nokia SR Linux routers.",
        topology_template=CAMPUS_CORE_ROUTING_SCENARIO_ID,
        objective="Restore the expected campus client connectivity across the four-router SR Linux core.",
        story=(
            "A campus core has two access/client segments and redundant SR Linux core paths. "
            "Use the expected design requirements to verify addressing, interface state, and routing."
        ),
        topology_metadata={
            "topology_type": "campus_core_routing",
            "device_count": 6,
            "router_count": 4,
            "client_count": 2,
            "link_count": 6,
            "devices": ["client1", "srl1", "srl3", "srl4", "srl2", "client2"],
        },
        devices=[
            {"id": "client1", "label": "Campus Client 1", "role": "client", "os": "Linux", "image": NETWORK_CLIENT_IMAGE, "cli_profile": "linux_shell"},
            {"id": "client2", "label": "Campus Client 2", "role": "client", "os": "Linux", "image": NETWORK_CLIENT_IMAGE, "cli_profile": "linux_shell"},
            {"id": "srl1", "label": "Campus Edge Router 1", "role": "edge_router", "os": "Nokia SR Linux", "image": SR_LINUX_IMAGE, "cli_profile": "sr_cli"},
            {"id": "srl2", "label": "Campus Edge Router 2", "role": "edge_router", "os": "Nokia SR Linux", "image": SR_LINUX_IMAGE, "cli_profile": "sr_cli"},
            {"id": "srl3", "label": "Campus Core Router 3", "role": "core_router", "os": "Nokia SR Linux", "image": SR_LINUX_IMAGE, "cli_profile": "sr_cli"},
            {"id": "srl4", "label": "Campus Core Router 4", "role": "core_router", "os": "Nokia SR Linux", "image": SR_LINUX_IMAGE, "cli_profile": "sr_cli"},
        ],
        links=[
            {"source": {"node": "client1", "interface": "eth1"}, "target": {"node": "srl1", "interface": "ethernet-1/1"}, "subnet": "10.10.10.0/24"},
            {"source": {"node": "srl1", "interface": "ethernet-1/2"}, "target": {"node": "srl3", "interface": "ethernet-1/1"}, "subnet": "10.10.13.0/30"},
            {"source": {"node": "srl3", "interface": "ethernet-1/2"}, "target": {"node": "srl2", "interface": "ethernet-1/2"}, "subnet": "10.10.23.0/30"},
            {"source": {"node": "srl2", "interface": "ethernet-1/1"}, "target": {"node": "client2", "interface": "eth1"}, "subnet": "10.10.20.0/24"},
            {"source": {"node": "srl1", "interface": "ethernet-1/3"}, "target": {"node": "srl4", "interface": "ethernet-1/1"}, "subnet": "10.10.14.0/30"},
            {"source": {"node": "srl4", "interface": "ethernet-1/2"}, "target": {"node": "srl2", "interface": "ethernet-1/3"}, "subnet": "10.10.24.0/30"},
        ],
        addressing_table=[
            {"device": "client1", "interface": "eth1", "ip_address": "10.10.10.10/24", "default_gateway": "10.10.10.1", "connects_to": "srl1 ethernet-1/1"},
            {"device": "client2", "interface": "eth1", "ip_address": "10.10.20.10/24", "default_gateway": "10.10.20.1", "connects_to": "srl2 ethernet-1/1"},
            {"device": "srl1", "interface": "ethernet-1/1", "ip_address": "10.10.10.1/24", "connects_to": "client1 eth1"},
            {"device": "srl1", "interface": "ethernet-1/2", "ip_address": "10.10.13.1/30", "connects_to": "srl3 ethernet-1/1"},
            {"device": "srl1", "interface": "ethernet-1/3", "ip_address": "10.10.14.1/30", "connects_to": "srl4 ethernet-1/1"},
            {"device": "srl2", "interface": "ethernet-1/1", "ip_address": "10.10.20.1/24", "connects_to": "client2 eth1"},
            {"device": "srl2", "interface": "ethernet-1/2", "ip_address": "10.10.23.1/30", "connects_to": "srl3 ethernet-1/2"},
            {"device": "srl2", "interface": "ethernet-1/3", "ip_address": "10.10.24.1/30", "connects_to": "srl4 ethernet-1/2"},
            {"device": "srl3", "interface": "ethernet-1/1", "ip_address": "10.10.13.2/30", "connects_to": "srl1 ethernet-1/2"},
            {"device": "srl3", "interface": "ethernet-1/2", "ip_address": "10.10.23.2/30", "connects_to": "srl2 ethernet-1/2"},
            {"device": "srl4", "interface": "ethernet-1/1", "ip_address": "10.10.14.2/30", "connects_to": "srl1 ethernet-1/3"},
            {"device": "srl4", "interface": "ethernet-1/2", "ip_address": "10.10.24.2/30", "connects_to": "srl2 ethernet-1/3"},
        ],
        interface_requirements=[
            {"device": "client1", "interface": "eth1", "required_state": "up", "required_ip": "10.10.10.10/24"},
            {"device": "client2", "interface": "eth1", "required_state": "up", "required_ip": "10.10.20.10/24"},
            {"device": "srl1", "interface": "ethernet-1/1.0", "required_state": "up", "required_ip": "10.10.10.1/24", "network_instance": "default"},
            {"device": "srl1", "interface": "ethernet-1/2.0", "required_state": "up", "required_ip": "10.10.13.1/30", "network_instance": "default"},
            {"device": "srl1", "interface": "ethernet-1/3.0", "required_state": "up", "required_ip": "10.10.14.1/30", "network_instance": "default"},
            {"device": "srl2", "interface": "ethernet-1/1.0", "required_state": "up", "required_ip": "10.10.20.1/24", "network_instance": "default"},
            {"device": "srl2", "interface": "ethernet-1/2.0", "required_state": "up", "required_ip": "10.10.23.1/30", "network_instance": "default"},
            {"device": "srl2", "interface": "ethernet-1/3.0", "required_state": "up", "required_ip": "10.10.24.1/30", "network_instance": "default"},
            {"device": "srl3", "interface": "ethernet-1/1.0", "required_state": "up", "required_ip": "10.10.13.2/30", "network_instance": "default"},
            {"device": "srl3", "interface": "ethernet-1/2.0", "required_state": "up", "required_ip": "10.10.23.2/30", "network_instance": "default"},
            {"device": "srl4", "interface": "ethernet-1/1.0", "required_state": "up", "required_ip": "10.10.14.2/30", "network_instance": "default"},
            {"device": "srl4", "interface": "ethernet-1/2.0", "required_state": "up", "required_ip": "10.10.24.2/30", "network_instance": "default"},
        ],
        routing_requirements=[
            {"device": "client1", "requirement": "client1 should use 10.10.10.1 as its default gateway."},
            {"device": "client2", "requirement": "client2 should use 10.10.20.1 as its default gateway."},
            {"device": "srl1", "requirement": "srl1 should route toward 10.10.20.0/24 through the SR Linux core."},
            {"device": "srl2", "requirement": "srl2 should route toward 10.10.10.0/24 through the SR Linux core."},
            {"device": "srl3", "requirement": "srl3 should provide the upper transit path between srl1 and srl2."},
            {"device": "srl4", "requirement": "srl4 should provide the lower transit path between srl1 and srl2."},
        ],
        static_routing_table=[
            {"device": "srl1", "destination": "10.10.20.0/24", "next_hop": "10.10.13.2", "path": "primary path toward client2 via srl3"},
            {"device": "srl2", "destination": "10.10.10.0/24", "next_hop": "10.10.23.2", "path": "primary path toward client1 via srl3"},
            {"device": "srl3", "destination": "10.10.10.0/24", "next_hop": "10.10.13.1", "path": "return path toward client1 edge"},
            {"device": "srl3", "destination": "10.10.20.0/24", "next_hop": "10.10.23.1", "path": "forward path toward client2 edge"},
            {"device": "srl4", "destination": "10.10.10.0/24", "next_hop": "10.10.14.1", "path": "alternate lower-core path toward client1 edge"},
            {"device": "srl4", "destination": "10.10.20.0/24", "next_hop": "10.10.24.1", "path": "alternate lower-core path toward client2 edge"},
        ],
        expected_connectivity=[
            {"source": "client1", "destination": "10.10.20.10", "protocol": "ICMP", "expectation": "client1 can ping client2 across the campus core."},
            {"source": "client2", "destination": "10.10.10.10", "protocol": "ICMP", "expectation": "client2 can ping client1 across the campus core."},
        ],
        student_tasks=[
            "Inspect all six campus devices and their roles.",
            "Review the campus addressing and interface requirements.",
            "Verify client gateways and SR Linux core routing.",
            "Restore expected campus connectivity and run validation.",
        ],
    ),
}


def resolve_scenario_id(scenario_id: str | None) -> str | None:
    if not scenario_id:
        return None

    return SCENARIO_ALIASES.get(scenario_id, scenario_id)


def list_scenarios() -> list[dict]:
    return [deepcopy(_SCENARIOS[scenario_id]) for scenario_id in _SCENARIOS]


def get_scenario(scenario_id: str | None) -> dict | None:
    canonical_id = resolve_scenario_id(scenario_id)

    if not canonical_id:
        return None

    scenario = _SCENARIOS.get(canonical_id)

    if scenario is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported scenario_id: {scenario_id}",
        )

    result = deepcopy(scenario)

    if scenario_id != canonical_id:
        result["requested_id"] = scenario_id
        result["legacy_alias"] = scenario_id

    return result


def is_srlinux_scenario(scenario_id: str | None) -> bool:
    return resolve_scenario_id(scenario_id) in _SCENARIOS


def is_deploy_only_scenario(scenario_id: str | None) -> bool:
    canonical_id = resolve_scenario_id(scenario_id)

    return canonical_id in DEPLOY_ONLY_SCENARIO_IDS
