import re
from typing import Any


NORMALIZED_NETWORK_TOPICS = (
    "ip_addressing",
    "default_gateway",
    "static_routing",
    "interface_state",
    "connectivity_testing",
    "network_instance",
    "terminal_usage",
    "lab_lifecycle",
    "general_troubleshooting",
)


TOPIC_LABELS = {
    "ip_addressing": "IP Addressing",
    "default_gateway": "Default Gateway",
    "static_routing": "Static Routing",
    "interface_state": "Interface State",
    "connectivity_testing": "Connectivity Testing",
    "network_instance": "Network Instance",
    "terminal_usage": "Terminal Usage",
    "lab_lifecycle": "Lab Lifecycle",
    "general_troubleshooting": "General Troubleshooting",
    "subnetting": "Subnetting",
    "interface_status": "Interface State",
    "routing": "Static Routing",
    "connectivity": "Connectivity Testing",
    "vlan": "VLAN",
    "vlan_like": "VLAN-like Configuration",
    "acl": "ACL",
    "acl_like": "ACL-like Policy",
    "trunk_configuration": "Trunk Configuration",
    "unknown": "General Troubleshooting",
}


TOPIC_ALIASES = {
    "": "general_troubleshooting",
    "unknown": "general_troubleshooting",
    "general": "general_troubleshooting",
    "troubleshooting": "general_troubleshooting",
    "general_troubleshooting": "general_troubleshooting",
    "ip": "ip_addressing",
    "ip_address": "ip_addressing",
    "ip_addresses": "ip_addressing",
    "addressing": "ip_addressing",
    "ip_addressing": "ip_addressing",
    "subnet": "ip_addressing",
    "subnetting": "ip_addressing",
    "gateway": "default_gateway",
    "default_gateway": "default_gateway",
    "wrong_gateway": "default_gateway",
    "routing": "static_routing",
    "route": "static_routing",
    "routes": "static_routing",
    "static_route": "static_routing",
    "static_routes": "static_routing",
    "static_routing": "static_routing",
    "interface": "interface_state",
    "interfaces": "interface_state",
    "interface_status": "interface_state",
    "interface_state": "interface_state",
    "link_state": "interface_state",
    "connectivity": "connectivity_testing",
    "connectivity_test": "connectivity_testing",
    "connectivity_testing": "connectivity_testing",
    "ping": "connectivity_testing",
    "network_instance": "network_instance",
    "network_instances": "network_instance",
    "network_instance_binding": "network_instance",
    "terminal": "terminal_usage",
    "terminal_usage": "terminal_usage",
    "web_cli": "terminal_usage",
    "lab_lifecycle": "lab_lifecycle",
    "runtime": "lab_lifecycle",
    "deployment": "lab_lifecycle",
    "vlan": "general_troubleshooting",
    "vlan_like": "general_troubleshooting",
    "acl": "general_troubleshooting",
    "acl_like": "general_troubleshooting",
    "trunk_configuration": "general_troubleshooting",
}


TOPIC_HINTS = {
    "ip_addressing": "Check interface IPv4 addresses, prefixes, and addressing table consistency.",
    "default_gateway": "Review the client default gateway configuration and verify that it points to the correct gateway device.",
    "static_routing": "Compare the routing table with the expected destination networks and next-hop reachability.",
    "interface_state": "Check that the expected interfaces are present, up, and carrying the correct Layer 3 state.",
    "connectivity_testing": "Test end-to-end connectivity after each correction and isolate whether the failure is local or routed.",
    "network_instance": "Verify SR Linux network-instance bindings for the relevant subinterfaces.",
    "terminal_usage": "Use the terminal to inspect state carefully before applying changes.",
    "lab_lifecycle": "Deploy, validate, finish, or clean up the lab according to its current lifecycle state.",
    "general_troubleshooting": "Review the failed validation checks and troubleshoot layer by layer.",
    "subnetting": "Check interface IPv4 addresses, prefixes, and addressing table consistency.",
    "interface_status": "Check that the expected interfaces are present, up, and carrying the correct Layer 3 state.",
    "routing": "Compare the routing table with the expected destination networks and next-hop reachability.",
    "connectivity": "Test end-to-end connectivity after each correction and isolate whether the failure is local or routed.",
    "unknown": "Review the failed validation checks and troubleshoot layer by layer.",
}


TOPIC_NEXT_ACTIONS = {
    "ip_addressing": [
        "Compare the device interface address with the scenario addressing table.",
        "Verify the prefix length on the interface before testing connectivity.",
        "Re-run validation after confirming the address is on the expected subnet.",
    ],
    "default_gateway": [
        "Review the client default gateway configuration.",
        "Confirm that the default route points toward the correct gateway device.",
        "Test local gateway reachability before testing end-to-end connectivity.",
    ],
    "static_routing": [
        "Compare the routing table with the expected destination networks.",
        "Check next-hop reachability for each static route.",
        "Verify that return-path routes exist before repeating connectivity tests.",
    ],
    "interface_state": [
        "Inspect the relevant interface state and assigned Layer 3 address.",
        "Confirm that the expected interface appears in the running state output.",
        "Check the connected link before changing routing configuration.",
    ],
    "connectivity_testing": [
        "Test end-to-end connectivity after each correction.",
        "Use ping results to decide whether the issue is local addressing, gateway, or routing.",
        "Validate both traffic directions when troubleshooting routed paths.",
    ],
    "network_instance": [
        "Verify that the SR Linux subinterface is attached to the expected network instance.",
        "Check the network-instance interface list before changing routes.",
    ],
    "terminal_usage": [
        "Use the terminal to inspect current state before applying changes.",
        "Keep command output available so you can compare before and after states.",
    ],
    "lab_lifecycle": [
        "Deploy the lab before validating runtime state.",
        "Finish or clean up the lab after completing the troubleshooting task.",
    ],
    "general_troubleshooting": [
        "Read the failed validation message carefully.",
        "Troubleshoot in order: interface, addressing, gateway, routing, and connectivity.",
    ],
}


VALIDATION_CHECK_TOPIC_OVERRIDES = {
    "srl_check_1_router_gateway_address": "ip_addressing",
    "srl_check_2_router_network_instance": "network_instance",
    "srl_check_3_client_address": "ip_addressing",
    "srl_check_4_client_default_gateway": "default_gateway",
    "srl_check_5_gateway_connectivity": "connectivity_testing",
    "campus_check_1_client1_address": "ip_addressing",
    "campus_check_2_client1_default_gateway": "default_gateway",
    "campus_check_3_client2_address": "ip_addressing",
    "campus_check_4_client2_default_gateway": "default_gateway",
    "campus_check_5_client1_to_client2_connectivity": "connectivity_testing",
    "campus_check_6_client2_to_client1_connectivity": "connectivity_testing",
    "campus_check_7_srl1_edge_and_core_interfaces": "interface_state",
    "campus_check_8_srl2_edge_and_core_interfaces": "interface_state",
    "campus_check_9_srl3_transit_routes": "static_routing",
    "campus_check_10_srl1_route_to_client2": "static_routing",
    "campus_check_11_srl2_route_to_client1": "static_routing",
    "campus_check_runtime_deployed": "lab_lifecycle",
}


def normalize_network_topic(value: Any) -> str:
    if value is None:
        return "general_troubleshooting"

    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")

    return TOPIC_ALIASES.get(text, text if text in NORMALIZED_NETWORK_TOPICS else "general_troubleshooting")


def topic_for_validation_check(check_id: Any, fallback_topic: Any = None) -> str:
    check_key = str(check_id or "").strip()

    if check_key in VALIDATION_CHECK_TOPIC_OVERRIDES:
        return VALIDATION_CHECK_TOPIC_OVERRIDES[check_key]

    return normalize_network_topic(fallback_topic)


def network_topic_label(topic: Any) -> str:
    topic_key = normalize_network_topic(topic)
    return TOPIC_LABELS.get(topic_key, topic_key.replace("_", " ").title())


def network_topic_hint(topic: Any) -> str:
    topic_key = normalize_network_topic(topic)
    return TOPIC_HINTS.get(topic_key, TOPIC_HINTS["general_troubleshooting"])


def network_topic_next_actions(topic: Any) -> list[str]:
    topic_key = normalize_network_topic(topic)
    return list(TOPIC_NEXT_ACTIONS.get(topic_key, TOPIC_NEXT_ACTIONS["general_troubleshooting"]))


def scenario_id_from_session(session: dict[str, Any]) -> str:
    scenario = session.get("scenario")

    if isinstance(scenario, dict):
        scenario_id = scenario.get("id") or scenario.get("scenario_id")
        if scenario_id:
            return str(scenario_id)

    topology = session.get("topology")
    if isinstance(topology, dict):
        scenario_id = topology.get("scenario_id") or topology.get("scenario")
        if isinstance(scenario_id, str) and scenario_id.strip():
            return scenario_id.strip()

    topology_template = session.get("topology_template")
    if topology_template:
        return str(topology_template)

    return "unknown"
