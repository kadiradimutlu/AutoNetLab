import hashlib
import subprocess
from typing import Any

from app.schemas.enums import SessionStatus
from app.services.scenario_catalog import (
    BRANCH_STATIC_ROUTING_SCENARIO_ID,
    CAMPUS_CORE_ROUTING_SCENARIO_ID,
    CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID,
    SR_BASIC_LINK_SCENARIO_ID,
    SR_EDGE_LINK_SCENARIO_ID,
    resolve_scenario_id,
)


SRLINUX_CLIENT_EXPECTED_GATEWAY = "10.10.10.1"
SRLINUX_CLIENT_INJECTED_GATEWAY = "10.10.10.254"
SRLINUX_WRONG_CLIENT_GATEWAY_CODE = "SRLINUX_WRONG_CLIENT_GATEWAY"
SRLINUX_WRONG_CLIENT_GATEWAY_VARIANT_ID = "srl_basic_link_client_wrong_default_gateway"

CAMPUS_CLIENT2_EXPECTED_GATEWAY = "10.10.20.1"
CAMPUS_CLIENT2_INJECTED_GATEWAY = "10.10.20.254"
CAMPUS_WRONG_CLIENT2_GATEWAY_CODE = "CAMPUS_CLIENT2_WRONG_GATEWAY"
CAMPUS_WRONG_CLIENT2_GATEWAY_VARIANT_ID = "campus_client2_wrong_gateway"

BRANCH_CLIENT2_EXPECTED_GATEWAY = "10.10.20.1"
BRANCH_CLIENT2_INJECTED_GATEWAY = "10.10.20.254"
BRANCH_WRONG_CLIENT2_GATEWAY_CODE = "BRANCH_CLIENT2_WRONG_GATEWAY"
BRANCH_WRONG_CLIENT2_GATEWAY_VARIANT_ID = "branch_client2_wrong_gateway"


BRANCH_CLIENTS: dict[str, dict[str, str]] = {
    "client1": {
        "interface": "eth1",
        "ip_address": "10.10.10.10/24",
        "default_gateway": "10.10.10.1",
        "remote_peer": "10.10.20.10",
    },
    "client2": {
        "interface": "eth1",
        "ip_address": "10.10.20.10/24",
        "default_gateway": "10.10.20.1",
        "remote_peer": "10.10.10.10",
    },
}

BRANCH_SRL_INTERFACES: dict[str, list[dict[str, str]]] = {
    "srl1": [
        {"interface": "ethernet-1/1", "ip_address": "10.10.10.1/24"},
        {"interface": "ethernet-1/2", "ip_address": "10.10.12.1/30"},
    ],
    "srl2": [
        {"interface": "ethernet-1/1", "ip_address": "10.10.20.1/24"},
        {"interface": "ethernet-1/2", "ip_address": "10.10.12.2/30"},
    ],
}

BRANCH_STATIC_ROUTES: dict[str, list[dict[str, Any]]] = {
    "srl1": [
        {
            "prefix": "10.10.20.0/24",
            "next_hop": "10.10.12.2",
            "next_hop_id": 1,
            "group": "branch-srl1-to-client2",
        },
    ],
    "srl2": [
        {
            "prefix": "10.10.10.0/24",
            "next_hop": "10.10.12.1",
            "next_hop_id": 1,
            "group": "branch-srl2-to-client1",
        },
    ],
}


CAMPUS_CLIENTS: dict[str, dict[str, str]] = {
    "client1": {
        "interface": "eth1",
        "ip_address": "10.10.10.10/24",
        "default_gateway": "10.10.10.1",
        "remote_peer": "10.10.20.10",
    },
    "client2": {
        "interface": "eth1",
        "ip_address": "10.10.20.10/24",
        "default_gateway": "10.10.20.1",
        "remote_peer": "10.10.10.10",
    },
}

CAMPUS_SRL_INTERFACES: dict[str, list[dict[str, str]]] = {
    "srl1": [
        {"interface": "ethernet-1/1", "ip_address": "10.10.10.1/24"},
        {"interface": "ethernet-1/2", "ip_address": "10.10.13.1/30"},
        {"interface": "ethernet-1/3", "ip_address": "10.10.14.1/30"},
    ],
    "srl2": [
        {"interface": "ethernet-1/1", "ip_address": "10.10.20.1/24"},
        {"interface": "ethernet-1/2", "ip_address": "10.10.23.1/30"},
        {"interface": "ethernet-1/3", "ip_address": "10.10.24.1/30"},
    ],
    "srl3": [
        {"interface": "ethernet-1/1", "ip_address": "10.10.13.2/30"},
        {"interface": "ethernet-1/2", "ip_address": "10.10.23.2/30"},
    ],
    "srl4": [
        {"interface": "ethernet-1/1", "ip_address": "10.10.14.2/30"},
        {"interface": "ethernet-1/2", "ip_address": "10.10.24.2/30"},
    ],
}

CAMPUS_STATIC_ROUTES: dict[str, list[dict[str, Any]]] = {
    "srl1": [
        {
            "prefix": "10.10.20.0/24",
            "next_hop": "10.10.13.2",
            "next_hop_id": 1,
            "group": "campus-srl1-to-client2",
        },
    ],
    "srl2": [
        {
            "prefix": "10.10.10.0/24",
            "next_hop": "10.10.23.2",
            "next_hop_id": 1,
            "group": "campus-srl2-to-client1",
        },
    ],
    "srl3": [
        {
            "prefix": "10.10.10.0/24",
            "next_hop": "10.10.13.1",
            "next_hop_id": 1,
            "group": "campus-srl3-to-client1",
        },
        {
            "prefix": "10.10.20.0/24",
            "next_hop": "10.10.23.1",
            "next_hop_id": 2,
            "group": "campus-srl3-to-client2",
        },
    ],
    "srl4": [
        {
            "prefix": "10.10.10.0/24",
            "next_hop": "10.10.14.1",
            "next_hop_id": 1,
            "group": "campus-srl4-to-client1",
        },
        {
            "prefix": "10.10.20.0/24",
            "next_hop": "10.10.24.1",
            "next_hop_id": 2,
            "group": "campus-srl4-to-client2",
        },
    ],
}



def build_srlinux_runtime_faults(
    *,
    difficulty: Any,
    seed: str,
    scenario_id: str | None = None,
) -> list[dict[str, Any]]:
    """
    Builds deterministic, difficulty-aware SR Linux runtime faults.

    NR-Sprint40A:
    - easy selects 1 fault
    - medium selects 2 non-conflicting faults
    - hard selects 3 non-conflicting faults
    - selection is deterministic for the same session/scenario/difficulty
    - safe wrong values never equal the expected design value
    """

    scenario_key = resolve_scenario_id(scenario_id or SR_BASIC_LINK_SCENARIO_ID)
    fault_count = _fault_count_for_difficulty(difficulty)
    catalog = _runtime_fault_catalog_for_scenario(
        scenario_id=scenario_key,
        seed=seed,
    )

    return _select_faults_from_catalog(
        catalog=catalog,
        fault_count=fault_count,
        seed=seed,
        scenario_id=scenario_key,
        difficulty=difficulty,
    )


def _basic_link_client_wrong_gateway_fault() -> dict[str, Any]:
    return {
        "code": SRLINUX_WRONG_CLIENT_GATEWAY_CODE,
        "topic": "default_gateway",
        "device": "client1",
        "description": "client1 has an incorrect default gateway for the SR Linux link.",
        "severity": "medium",
        "variant_id": SRLINUX_WRONG_CLIENT_GATEWAY_VARIANT_ID,
        "scenario_id": SR_EDGE_LINK_SCENARIO_ID,
        "conflict_key": "client1_default_route",
        "interface": "eth1",
        "validation_command": "ip route",
        "expected_outputs": [f"default via {SRLINUX_CLIENT_EXPECTED_GATEWAY}"],
        "injection_commands": [
            f"ip route replace default via {SRLINUX_CLIENT_INJECTED_GATEWAY} dev eth1"
        ],
    }


def _branch_client2_wrong_gateway_fault() -> dict[str, Any]:
    return {
        "code": BRANCH_WRONG_CLIENT2_GATEWAY_CODE,
        "topic": "default_gateway",
        "device": "client2",
        "description": "client2 has an incorrect default gateway for the branch client segment.",
        "severity": "medium",
        "variant_id": BRANCH_WRONG_CLIENT2_GATEWAY_VARIANT_ID,
        "scenario_id": BRANCH_STATIC_ROUTING_SCENARIO_ID,
        "conflict_key": "client2_default_route",
        "interface": "eth1",
        "validation_command": "ip route",
        "expected_outputs": [f"default via {BRANCH_CLIENT2_EXPECTED_GATEWAY}"],
        "injection_commands": [
            f"ip route replace default via {BRANCH_CLIENT2_INJECTED_GATEWAY} dev eth1"
        ],
    }


def _campus_client2_wrong_gateway_fault() -> dict[str, Any]:
    return {
        "code": CAMPUS_WRONG_CLIENT2_GATEWAY_CODE,
        "topic": "default_gateway",
        "device": "client2",
        "description": "client2 has an incorrect default gateway for the campus client segment.",
        "severity": "medium",
        "variant_id": CAMPUS_WRONG_CLIENT2_GATEWAY_VARIANT_ID,
        "scenario_id": CAMPUS_CORE_ROUTING_SCENARIO_ID,
        "conflict_key": "client2_default_route",
        "interface": "eth1",
        "validation_command": "ip route",
        "expected_outputs": [f"default via {CAMPUS_CLIENT2_EXPECTED_GATEWAY}"],
        "injection_commands": [
            f"ip route replace default via {CAMPUS_CLIENT2_INJECTED_GATEWAY} dev eth1"
        ],
    }


def _fault_count_for_difficulty(difficulty: Any) -> int:
    value = getattr(difficulty, "value", difficulty)
    normalized = str(value or "easy").lower()

    return {
        "easy": 1,
        "medium": 2,
        "hard": 3,
    }.get(normalized, 1)


def _runtime_fault_catalog_for_scenario(
    *,
    scenario_id: str | None,
    seed: str,
) -> list[dict[str, Any]]:
    scenario_key = resolve_scenario_id(scenario_id or SR_BASIC_LINK_SCENARIO_ID)

    if scenario_key == BRANCH_STATIC_ROUTING_SCENARIO_ID:
        return _branch_runtime_fault_catalog(seed=seed)

    if scenario_key == CAMPUS_CORE_ROUTING_SCENARIO_ID:
        return _campus_runtime_fault_catalog(seed=seed)

    return _edge_runtime_fault_catalog(seed=seed)


def _edge_runtime_fault_catalog(*, seed: str) -> list[dict[str, Any]]:
    return [
        _basic_link_client_wrong_gateway_fault(),
        _client_missing_default_route_fault(
            scenario_id=SR_EDGE_LINK_SCENARIO_ID,
            variant_id="edge_client1_missing_default_route",
            device="client1",
            interface="eth1",
            expected_gateway=SRLINUX_CLIENT_EXPECTED_GATEWAY,
            conflict_key="client1_default_route",
        ),
        _client_wrong_ip_fault(
            scenario_id=SR_EDGE_LINK_SCENARIO_ID,
            variant_id="edge_client1_wrong_ip",
            seed=seed,
            device="client1",
            interface="eth1",
            expected_ip="10.10.10.10/24",
            wrong_ip_candidates=["10.10.10.99/24", "10.10.10.200/24", "10.10.11.10/24"],
            conflict_key="client1_eth1_ip",
        ),
        _client_missing_ip_fault(
            scenario_id=SR_EDGE_LINK_SCENARIO_ID,
            variant_id="edge_client1_missing_ip",
            device="client1",
            interface="eth1",
            expected_ip="10.10.10.10/24",
            conflict_key="client1_eth1_ip",
        ),
        _client_interface_down_fault(
            scenario_id=SR_EDGE_LINK_SCENARIO_ID,
            variant_id="edge_client1_interface_down",
            device="client1",
            interface="eth1",
            conflict_key="client1_eth1_state",
        ),
        _srl_network_instance_unbind_fault(
            scenario_id=SR_EDGE_LINK_SCENARIO_ID,
            variant_id="edge_srl1_missing_network_instance_binding",
            device="srl1",
            interface="ethernet-1/1",
            conflict_key="srl1_e1_1_ni",
        ),
        _srl_wrong_interface_ip_fault(
            scenario_id=SR_EDGE_LINK_SCENARIO_ID,
            variant_id="edge_srl1_wrong_gateway_ip",
            seed=seed,
            device="srl1",
            interface="ethernet-1/1",
            expected_ip="10.10.10.1/24",
            wrong_ip_candidates=["10.10.10.254/24", "10.10.10.99/24", "10.10.11.1/24"],
            conflict_key="srl1_e1_1_ip",
        ),
        _srl_interface_admin_down_fault(
            scenario_id=SR_EDGE_LINK_SCENARIO_ID,
            variant_id="edge_srl1_interface_admin_down",
            device="srl1",
            interface="ethernet-1/1",
            conflict_key="srl1_e1_1_state",
        ),
        _srl_subinterface_ipv4_disable_fault(
            scenario_id=SR_EDGE_LINK_SCENARIO_ID,
            variant_id="edge_srl1_subinterface_ipv4_disabled",
            device="srl1",
            interface="ethernet-1/1",
            conflict_key="srl1_e1_1_ipv4_state",
        ),
        _client_wrong_ip_fault(
            scenario_id=SR_EDGE_LINK_SCENARIO_ID,
            variant_id="edge_client1_wrong_subnet_mask",
            seed=seed,
            device="client1",
            interface="eth1",
            expected_ip="10.10.10.10/24",
            wrong_ip_candidates=["10.10.10.10/25", "10.10.10.10/26", "10.10.10.10/27"],
            conflict_key="client1_eth1_ip",
        ),
    ]


def _branch_runtime_fault_catalog(*, seed: str) -> list[dict[str, Any]]:
    return [
        _client_wrong_gateway_fault(
            scenario_id=BRANCH_STATIC_ROUTING_SCENARIO_ID,
            variant_id="branch_client1_wrong_gateway",
            seed=seed,
            device="client1",
            interface="eth1",
            expected_gateway="10.10.10.1",
            wrong_gateway_candidates=["10.10.10.254", "10.10.10.99", "10.10.11.1"],
            conflict_key="client1_default_route",
        ),
        _branch_client2_wrong_gateway_fault(),
        _client_missing_default_route_fault(
            scenario_id=BRANCH_STATIC_ROUTING_SCENARIO_ID,
            variant_id="branch_client1_missing_default_route",
            device="client1",
            interface="eth1",
            expected_gateway="10.10.10.1",
            conflict_key="client1_default_route",
        ),
        _client_missing_default_route_fault(
            scenario_id=BRANCH_STATIC_ROUTING_SCENARIO_ID,
            variant_id="branch_client2_missing_default_route",
            device="client2",
            interface="eth1",
            expected_gateway="10.10.20.1",
            conflict_key="client2_default_route",
        ),
        _client_wrong_ip_fault(
            scenario_id=BRANCH_STATIC_ROUTING_SCENARIO_ID,
            variant_id="branch_client1_wrong_ip",
            seed=seed,
            device="client1",
            interface="eth1",
            expected_ip="10.10.10.10/24",
            wrong_ip_candidates=["10.10.10.99/24", "10.10.10.200/24", "10.10.11.10/24"],
            conflict_key="client1_eth1_ip",
        ),
        _client_wrong_ip_fault(
            scenario_id=BRANCH_STATIC_ROUTING_SCENARIO_ID,
            variant_id="branch_client2_wrong_ip",
            seed=seed,
            device="client2",
            interface="eth1",
            expected_ip="10.10.20.10/24",
            wrong_ip_candidates=["10.10.20.99/24", "10.10.20.200/24", "10.10.21.10/24"],
            conflict_key="client2_eth1_ip",
        ),
        _client_interface_down_fault(
            scenario_id=BRANCH_STATIC_ROUTING_SCENARIO_ID,
            variant_id="branch_client1_interface_down",
            device="client1",
            interface="eth1",
            conflict_key="client1_eth1_state",
        ),
        _client_interface_down_fault(
            scenario_id=BRANCH_STATIC_ROUTING_SCENARIO_ID,
            variant_id="branch_client2_interface_down",
            device="client2",
            interface="eth1",
            conflict_key="client2_eth1_state",
        ),
        _srl_interface_admin_down_fault(
            scenario_id=BRANCH_STATIC_ROUTING_SCENARIO_ID,
            variant_id="branch_srl1_lan_interface_down",
            device="srl1",
            interface="ethernet-1/1",
            conflict_key="srl1_e1_1_state",
        ),
        _srl_interface_admin_down_fault(
            scenario_id=BRANCH_STATIC_ROUTING_SCENARIO_ID,
            variant_id="branch_srl2_lan_interface_down",
            device="srl2",
            interface="ethernet-1/1",
            conflict_key="srl2_e1_1_state",
        ),
        _srl_interface_admin_down_fault(
            scenario_id=BRANCH_STATIC_ROUTING_SCENARIO_ID,
            variant_id="branch_srl1_transit_interface_down",
            device="srl1",
            interface="ethernet-1/2",
            conflict_key="branch_transit_state",
        ),
        _srl_interface_admin_down_fault(
            scenario_id=BRANCH_STATIC_ROUTING_SCENARIO_ID,
            variant_id="branch_srl2_transit_interface_down",
            device="srl2",
            interface="ethernet-1/2",
            conflict_key="branch_transit_state",
        ),
        _srl_missing_static_route_fault(
            scenario_id=BRANCH_STATIC_ROUTING_SCENARIO_ID,
            variant_id="branch_srl1_missing_route_to_client2",
            device="srl1",
            prefix="10.10.20.0/24",
            expected_output="branch-srl1-to-client2",
            conflict_key="srl1_to_client2_route",
        ),
        _srl_missing_static_route_fault(
            scenario_id=BRANCH_STATIC_ROUTING_SCENARIO_ID,
            variant_id="branch_srl2_missing_route_to_client1",
            device="srl2",
            prefix="10.10.10.0/24",
            expected_output="branch-srl2-to-client1",
            conflict_key="srl2_to_client1_route",
        ),
        _srl_wrong_static_route_next_hop_fault(
            scenario_id=BRANCH_STATIC_ROUTING_SCENARIO_ID,
            variant_id="branch_srl1_wrong_next_hop_to_client2",
            device="srl1",
            prefix="10.10.20.0/24",
            wrong_next_hop="10.10.12.6",
            expected_output="branch-srl1-to-client2",
            conflict_key="srl1_to_client2_route",
        ),
        _srl_wrong_static_route_next_hop_fault(
            scenario_id=BRANCH_STATIC_ROUTING_SCENARIO_ID,
            variant_id="branch_srl2_wrong_next_hop_to_client1",
            device="srl2",
            prefix="10.10.10.0/24",
            wrong_next_hop="10.10.12.5",
            expected_output="branch-srl2-to-client1",
            conflict_key="srl2_to_client1_route",
        ),
    ]


def _campus_runtime_fault_catalog(*, seed: str) -> list[dict[str, Any]]:
    return [
        _client_wrong_gateway_fault(
            scenario_id=CAMPUS_CORE_ROUTING_SCENARIO_ID,
            variant_id="campus_client1_wrong_gateway",
            seed=seed,
            device="client1",
            interface="eth1",
            expected_gateway="10.10.10.1",
            wrong_gateway_candidates=["10.10.10.254", "10.10.10.99", "10.10.11.1"],
            conflict_key="client1_default_route",
        ),
        _campus_client2_wrong_gateway_fault(),
        _client_missing_default_route_fault(
            scenario_id=CAMPUS_CORE_ROUTING_SCENARIO_ID,
            variant_id="campus_client1_missing_default_route",
            device="client1",
            interface="eth1",
            expected_gateway="10.10.10.1",
            conflict_key="client1_default_route",
        ),
        _client_missing_default_route_fault(
            scenario_id=CAMPUS_CORE_ROUTING_SCENARIO_ID,
            variant_id="campus_client2_missing_default_route",
            device="client2",
            interface="eth1",
            expected_gateway="10.10.20.1",
            conflict_key="client2_default_route",
        ),
        _client_wrong_ip_fault(
            scenario_id=CAMPUS_CORE_ROUTING_SCENARIO_ID,
            variant_id="campus_client1_wrong_ip",
            seed=seed,
            device="client1",
            interface="eth1",
            expected_ip="10.10.10.10/24",
            wrong_ip_candidates=["10.10.10.99/24", "10.10.10.200/24", "10.10.11.10/24"],
            conflict_key="client1_eth1_ip",
        ),
        _client_wrong_ip_fault(
            scenario_id=CAMPUS_CORE_ROUTING_SCENARIO_ID,
            variant_id="campus_client2_wrong_ip",
            seed=seed,
            device="client2",
            interface="eth1",
            expected_ip="10.10.20.10/24",
            wrong_ip_candidates=["10.10.20.99/24", "10.10.20.200/24", "10.10.21.10/24"],
            conflict_key="client2_eth1_ip",
        ),
        _srl_interface_admin_down_fault(
            scenario_id=CAMPUS_CORE_ROUTING_SCENARIO_ID,
            variant_id="campus_srl1_client_lan_interface_down",
            device="srl1",
            interface="ethernet-1/1",
            conflict_key="srl1_e1_1_state",
        ),
        _srl_interface_admin_down_fault(
            scenario_id=CAMPUS_CORE_ROUTING_SCENARIO_ID,
            variant_id="campus_srl2_client_lan_interface_down",
            device="srl2",
            interface="ethernet-1/1",
            conflict_key="srl2_e1_1_state",
        ),
        _srl_interface_admin_down_fault(
            scenario_id=CAMPUS_CORE_ROUTING_SCENARIO_ID,
            variant_id="campus_srl1_upper_core_interface_down",
            device="srl1",
            interface="ethernet-1/2",
            conflict_key="campus_upper_path_state",
        ),
        _srl_interface_admin_down_fault(
            scenario_id=CAMPUS_CORE_ROUTING_SCENARIO_ID,
            variant_id="campus_srl3_upper_core_interface_down",
            device="srl3",
            interface="ethernet-1/1",
            conflict_key="campus_upper_path_state",
        ),
        _srl_interface_admin_down_fault(
            scenario_id=CAMPUS_CORE_ROUTING_SCENARIO_ID,
            variant_id="campus_srl1_lower_core_interface_down",
            device="srl1",
            interface="ethernet-1/3",
            conflict_key="campus_lower_path_state",
        ),
        _srl_interface_admin_down_fault(
            scenario_id=CAMPUS_CORE_ROUTING_SCENARIO_ID,
            variant_id="campus_srl4_lower_core_interface_down",
            device="srl4",
            interface="ethernet-1/1",
            conflict_key="campus_lower_path_state",
        ),
        _srl_missing_static_route_fault(
            scenario_id=CAMPUS_CORE_ROUTING_SCENARIO_ID,
            variant_id="campus_srl1_missing_route_to_client2",
            device="srl1",
            prefix="10.10.20.0/24",
            expected_output="campus-srl1-to-client2",
            conflict_key="srl1_to_client2_route",
        ),
        _srl_missing_static_route_fault(
            scenario_id=CAMPUS_CORE_ROUTING_SCENARIO_ID,
            variant_id="campus_srl2_missing_route_to_client1",
            device="srl2",
            prefix="10.10.10.0/24",
            expected_output="campus-srl2-to-client1",
            conflict_key="srl2_to_client1_route",
        ),
        _srl_missing_static_route_fault(
            scenario_id=CAMPUS_CORE_ROUTING_SCENARIO_ID,
            variant_id="campus_srl3_missing_route_to_client1",
            device="srl3",
            prefix="10.10.10.0/24",
            expected_output="campus-srl3-to-client1",
            conflict_key="srl3_to_client1_route",
        ),
        _srl_missing_static_route_fault(
            scenario_id=CAMPUS_CORE_ROUTING_SCENARIO_ID,
            variant_id="campus_srl3_missing_route_to_client2",
            device="srl3",
            prefix="10.10.20.0/24",
            expected_output="campus-srl3-to-client2",
            conflict_key="srl3_to_client2_route",
        ),
        _srl_wrong_static_route_next_hop_fault(
            scenario_id=CAMPUS_CORE_ROUTING_SCENARIO_ID,
            variant_id="campus_srl1_wrong_next_hop_to_client2",
            device="srl1",
            prefix="10.10.20.0/24",
            wrong_next_hop="10.10.13.6",
            expected_output="campus-srl1-to-client2",
            conflict_key="srl1_to_client2_route",
        ),
        _srl_wrong_static_route_next_hop_fault(
            scenario_id=CAMPUS_CORE_ROUTING_SCENARIO_ID,
            variant_id="campus_srl2_wrong_next_hop_to_client1",
            device="srl2",
            prefix="10.10.10.0/24",
            wrong_next_hop="10.10.23.6",
            expected_output="campus-srl2-to-client1",
            conflict_key="srl2_to_client1_route",
        ),
        _srl_wrong_static_route_next_hop_fault(
            scenario_id=CAMPUS_CORE_ROUTING_SCENARIO_ID,
            variant_id="campus_srl3_wrong_next_hop_to_client1",
            device="srl3",
            prefix="10.10.10.0/24",
            wrong_next_hop="10.10.13.6",
            expected_output="campus-srl3-to-client1",
            conflict_key="srl3_to_client1_route",
        ),
        _srl_wrong_static_route_next_hop_fault(
            scenario_id=CAMPUS_CORE_ROUTING_SCENARIO_ID,
            variant_id="campus_srl3_wrong_next_hop_to_client2",
            device="srl3",
            prefix="10.10.20.0/24",
            wrong_next_hop="10.10.23.6",
            expected_output="campus-srl3-to-client2",
            conflict_key="srl3_to_client2_route",
        ),
    ]


def _select_faults_from_catalog(
    *,
    catalog: list[dict[str, Any]],
    fault_count: int,
    seed: str,
    scenario_id: str | None,
    difficulty: Any,
) -> list[dict[str, Any]]:
    if fault_count <= 0:
        return []

    selected: list[dict[str, Any]] = []
    used_conflict_keys: set[str] = set()

    primary_fault = _primary_fault_for_scenario(
        catalog=catalog,
        scenario_id=scenario_id,
    )
    if primary_fault is not None:
        _append_fault_if_available(
            selected=selected,
            used_conflict_keys=used_conflict_keys,
            fault=primary_fault,
        )

    shuffled = sorted(
        catalog,
        key=lambda fault: _stable_digest(
            seed,
            str(scenario_id or ""),
            str(getattr(difficulty, "value", difficulty)),
            str(fault.get("variant_id") or ""),
        ),
    )

    for fault in shuffled:
        if len(selected) >= fault_count:
            break

        _append_fault_if_available(
            selected=selected,
            used_conflict_keys=used_conflict_keys,
            fault=fault,
        )

    return selected[:fault_count]


def _primary_fault_for_scenario(
    *,
    catalog: list[dict[str, Any]],
    scenario_id: str | None,
) -> dict[str, Any] | None:
    primary_variant_by_scenario = {
        SR_EDGE_LINK_SCENARIO_ID: SRLINUX_WRONG_CLIENT_GATEWAY_VARIANT_ID,
        BRANCH_STATIC_ROUTING_SCENARIO_ID: BRANCH_WRONG_CLIENT2_GATEWAY_VARIANT_ID,
        CAMPUS_CORE_ROUTING_SCENARIO_ID: CAMPUS_WRONG_CLIENT2_GATEWAY_VARIANT_ID,
    }
    primary_variant_id = primary_variant_by_scenario.get(resolve_scenario_id(scenario_id))

    for fault in catalog:
        if fault.get("variant_id") == primary_variant_id:
            return fault

    return None


def _append_fault_if_available(
    *,
    selected: list[dict[str, Any]],
    used_conflict_keys: set[str],
    fault: dict[str, Any],
) -> None:
    variant_id = str(fault.get("variant_id") or "")

    if any(item.get("variant_id") == variant_id for item in selected):
        return

    conflict_key = str(fault.get("conflict_key") or variant_id)

    if conflict_key in used_conflict_keys:
        return

    selected.append(fault)
    used_conflict_keys.add(conflict_key)


def _client_wrong_gateway_fault(
    *,
    scenario_id: str,
    variant_id: str,
    seed: str,
    device: str,
    interface: str,
    expected_gateway: str,
    wrong_gateway_candidates: list[str],
    conflict_key: str,
) -> dict[str, Any]:
    wrong_gateway = _stable_choice(
        seed,
        variant_id,
        candidates=[
            candidate
            for candidate in wrong_gateway_candidates
            if candidate != expected_gateway
        ],
    )

    return _fault(
        scenario_id=scenario_id,
        variant_id=variant_id,
        topic="default_gateway",
        device=device,
        description=f"{device} has an incorrect default gateway.",
        severity="medium",
        conflict_key=conflict_key,
        validation_command="ip route",
        expected_outputs=[f"default via {expected_gateway}"],
        injection_commands=[
            f"ip route replace default via {wrong_gateway} dev {interface}"
        ],
    )


def _client_missing_default_route_fault(
    *,
    scenario_id: str,
    variant_id: str,
    device: str,
    interface: str,
    expected_gateway: str,
    conflict_key: str,
) -> dict[str, Any]:
    return _fault(
        scenario_id=scenario_id,
        variant_id=variant_id,
        topic="default_gateway",
        device=device,
        description=f"{device} is missing the expected default route.",
        severity="medium",
        conflict_key=conflict_key,
        validation_command="ip route",
        expected_outputs=[f"default via {expected_gateway}"],
        injection_commands=["ip route del default || true"],
    )


def _client_wrong_ip_fault(
    *,
    scenario_id: str,
    variant_id: str,
    seed: str,
    device: str,
    interface: str,
    expected_ip: str,
    wrong_ip_candidates: list[str],
    conflict_key: str,
) -> dict[str, Any]:
    wrong_ip = _stable_choice(
        seed,
        variant_id,
        candidates=[
            candidate
            for candidate in wrong_ip_candidates
            if candidate != expected_ip
        ],
    )

    return _fault(
        scenario_id=scenario_id,
        variant_id=variant_id,
        topic="ip_addressing",
        device=device,
        description=f"{device} has an incorrect IPv4 address or prefix on {interface}.",
        severity="medium",
        conflict_key=conflict_key,
        validation_command=f"ip -4 addr show dev {interface}",
        expected_outputs=[expected_ip],
        injection_commands=[
            f"ip addr flush dev {interface} || true && ip addr add {wrong_ip} dev {interface} && ip link set {interface} up"
        ],
    )


def _client_missing_ip_fault(
    *,
    scenario_id: str,
    variant_id: str,
    device: str,
    interface: str,
    expected_ip: str,
    conflict_key: str,
) -> dict[str, Any]:
    return _fault(
        scenario_id=scenario_id,
        variant_id=variant_id,
        topic="ip_addressing",
        device=device,
        description=f"{device} is missing the expected IPv4 address on {interface}.",
        severity="medium",
        conflict_key=conflict_key,
        validation_command=f"ip -4 addr show dev {interface}",
        expected_outputs=[expected_ip],
        injection_commands=[
            f"ip addr flush dev {interface} || true && ip link set {interface} up"
        ],
    )


def _client_interface_down_fault(
    *,
    scenario_id: str,
    variant_id: str,
    device: str,
    interface: str,
    conflict_key: str,
) -> dict[str, Any]:
    return _fault(
        scenario_id=scenario_id,
        variant_id=variant_id,
        topic="interface_state",
        device=device,
        description=f"{device} interface {interface} is administratively down.",
        severity="medium",
        conflict_key=conflict_key,
        validation_command=f"ip link show dev {interface}",
        expected_outputs=["state UP"],
        injection_commands=[f"ip link set {interface} down"],
    )


def _srl_network_instance_unbind_fault(
    *,
    scenario_id: str,
    variant_id: str,
    device: str,
    interface: str,
    conflict_key: str,
) -> dict[str, Any]:
    subinterface = _subinterface_name(interface)

    return _fault(
        scenario_id=scenario_id,
        variant_id=variant_id,
        topic="network_instance",
        device=device,
        description=f"{device} {subinterface} is missing from the default network-instance.",
        severity="medium",
        conflict_key=conflict_key,
        validation_command="info network-instance default",
        expected_outputs=[f"interface {subinterface}"],
        injection_commands=[
            _srl_cli_config_command([
                f"delete network-instance default interface {subinterface}",
            ])
        ],
    )


def _srl_wrong_interface_ip_fault(
    *,
    scenario_id: str,
    variant_id: str,
    seed: str,
    device: str,
    interface: str,
    expected_ip: str,
    wrong_ip_candidates: list[str],
    conflict_key: str,
) -> dict[str, Any]:
    wrong_ip = _stable_choice(
        seed,
        variant_id,
        candidates=[
            candidate
            for candidate in wrong_ip_candidates
            if candidate != expected_ip
        ],
    )

    return _fault(
        scenario_id=scenario_id,
        variant_id=variant_id,
        topic="ip_addressing",
        device=device,
        description=f"{device} {interface}.0 has an incorrect IPv4 address.",
        severity="medium",
        conflict_key=conflict_key,
        validation_command=f"info from state interface {interface} subinterface 0 ipv4",
        expected_outputs=[expected_ip],
        injection_commands=[
            _srl_cli_config_command([
                f"delete interface {interface} subinterface 0 ipv4 address {expected_ip}",
                f"set interface {interface} subinterface 0 ipv4 address {wrong_ip}",
            ])
        ],
    )


def _srl_interface_admin_down_fault(
    *,
    scenario_id: str,
    variant_id: str,
    device: str,
    interface: str,
    conflict_key: str,
) -> dict[str, Any]:
    return _fault(
        scenario_id=scenario_id,
        variant_id=variant_id,
        topic="interface_state",
        device=device,
        description=f"{device} {interface} is administratively disabled.",
        severity="medium",
        conflict_key=conflict_key,
        validation_command=f"info from state interface {interface}",
        expected_outputs=["admin-state enable"],
        injection_commands=[
            _srl_cli_config_command([
                f"set interface {interface} admin-state disable",
            ])
        ],
    )


def _srl_subinterface_ipv4_disable_fault(
    *,
    scenario_id: str,
    variant_id: str,
    device: str,
    interface: str,
    conflict_key: str,
) -> dict[str, Any]:
    return _fault(
        scenario_id=scenario_id,
        variant_id=variant_id,
        topic="interface_state",
        device=device,
        description=f"{device} {interface}.0 IPv4 is administratively disabled.",
        severity="medium",
        conflict_key=conflict_key,
        validation_command=f"info from state interface {interface} subinterface 0 ipv4",
        expected_outputs=["admin-state enable"],
        injection_commands=[
            _srl_cli_config_command([
                f"set interface {interface} subinterface 0 ipv4 admin-state disable",
            ])
        ],
    )


def _srl_missing_static_route_fault(
    *,
    scenario_id: str,
    variant_id: str,
    device: str,
    prefix: str,
    expected_output: str,
    conflict_key: str,
) -> dict[str, Any]:
    return _fault(
        scenario_id=scenario_id,
        variant_id=variant_id,
        topic="static_routing",
        device=device,
        description=f"{device} is missing the expected static route for {prefix}.",
        severity="medium",
        conflict_key=conflict_key,
        validation_command=f"info network-instance default static-routes route {prefix}",
        expected_outputs=[expected_output],
        injection_commands=[
            _srl_cli_config_command([
                f"delete network-instance default static-routes route {prefix}",
            ])
        ],
    )


def _srl_wrong_static_route_next_hop_fault(
    *,
    scenario_id: str,
    variant_id: str,
    device: str,
    prefix: str,
    wrong_next_hop: str,
    expected_output: str,
    conflict_key: str,
) -> dict[str, Any]:
    broken_group = f"{variant_id}-broken"

    return _fault(
        scenario_id=scenario_id,
        variant_id=variant_id,
        topic="static_routing",
        device=device,
        description=f"{device} static route for {prefix} points to an incorrect next-hop.",
        severity="medium",
        conflict_key=conflict_key,
        validation_command=f"info network-instance default static-routes route {prefix}",
        expected_outputs=[expected_output],
        injection_commands=[
            _srl_cli_config_command([
                "set network-instance default static next-hop 99 ip-address " + wrong_next_hop,
                f"set network-instance default static next-hop-group {broken_group} next-hop 99",
                f"set network-instance default static-routes route {prefix} static-next-hop-group {broken_group}",
            ])
        ],
    )


def _fault(
    *,
    scenario_id: str,
    variant_id: str,
    topic: str,
    device: str,
    description: str,
    severity: str,
    conflict_key: str,
    validation_command: str,
    expected_outputs: list[str],
    injection_commands: list[str],
) -> dict[str, Any]:
    return {
        "code": variant_id.upper(),
        "topic": topic,
        "device": device,
        "description": description,
        "severity": severity,
        "variant_id": variant_id,
        "scenario_id": scenario_id,
        "conflict_key": conflict_key,
        "validation_command": validation_command,
        "expected_outputs": expected_outputs,
        "injection_commands": injection_commands,
    }


def _srl_cli_config_command(commands: list[str]) -> str:
    quoted_lines = [
        "'enter candidate'",
        *[repr(command) for command in commands],
        "'commit now'",
        "'quit'",
    ]

    return "printf '%s\\n' " + " ".join(quoted_lines) + " | sr_cli"


def _stable_choice(seed: str, variant_id: str, candidates: list[str]) -> str:
    if not candidates:
        raise ValueError(f"No safe candidates were provided for {variant_id}.")

    index = int(_stable_digest(seed, variant_id), 16) % len(candidates)
    return candidates[index]


def _stable_digest(*parts: str) -> str:
    payload = "::".join(str(part) for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def apply_srlinux_runtime_setup(session: dict[str, Any]) -> dict[str, Any]:
    '''
    Applies runtime setup for supported SR Linux scenarios.

    Basic link keeps its existing Sprint 30 behavior and can still inject the
    wrong-gateway fault after baseline setup. Campus core static routing first applies the golden baseline, verifies it,
    and then applies a hidden, scenario-specific runtime fault so live validation
    can prove troubleshooting behavior.
    '''

    session_id = str(session["session_id"])
    scenario_id = _scenario_id(session)
    scenario_key = resolve_scenario_id(scenario_id or session.get("topology_template"))

    if scenario_key == SR_EDGE_LINK_SCENARIO_ID:
        return _apply_basic_link_runtime_setup(
            session=session,
            session_id=session_id,
        )

    if scenario_key == BRANCH_STATIC_ROUTING_SCENARIO_ID:
        return _apply_branch_static_routing_runtime_setup(
            session=session,
            session_id=session_id,
        )

    if scenario_key == CAMPUS_CORE_ROUTING_SCENARIO_ID:
        return _apply_campus_core_static_routing_runtime_setup(
            session=session,
            session_id=session_id,
        )

    return _success_response(
        session_id=session_id,
        command_results=[],
        message="No SR Linux runtime setup was required for this scenario.",
    )


def _apply_basic_link_runtime_setup(
    *,
    session: dict[str, Any],
    session_id: str,
) -> dict[str, Any]:
    client_container = _container_name_for_device(session, "client1")
    srl_container = _container_name_for_device(session, "srl1")

    if not client_container or not srl_container:
        return _error_response(
            session_id=session_id,
            command_results=[],
            error_code="SRLINUX_RUNTIME_METADATA_MISSING",
            detail="Could not resolve required container names for srl1/client1.",
        )

    command_results: list[dict[str, Any]] = []

    srl_config_script = "\n".join(
        [
            "enter candidate",
            "set network-instance default interface ethernet-1/1.0",
            "commit now",
            "quit",
            "",
        ]
    )

    srl_config_result = _run_docker_exec(
        container_name=srl_container,
        command=["sr_cli"],
        stage="srlinux_network_instance_setup",
        device="srl1",
        display_command="bind ethernet-1/1.0 to default network-instance",
        input_text=srl_config_script,
    )
    command_results.append(srl_config_result)

    if not srl_config_result["success"]:
        return _error_response(
            session_id=session_id,
            command_results=command_results,
            error_code="SRLINUX_NETWORK_INSTANCE_SETUP_FAILED",
            detail="Could not bind ethernet-1/1.0 to SR Linux default network-instance.",
        )

    client_setup_commands = [
        "ip addr flush dev eth1 || true",
        "ip addr add 10.10.10.10/24 dev eth1",
        "ip link set eth1 up",
        "ip route replace default via 10.10.10.1 dev eth1",
    ]

    for command in client_setup_commands:
        result = _run_docker_exec(
            container_name=client_container,
            command=["sh", "-lc", command],
            stage="client_runtime_setup",
            device="client1",
            display_command=command,
        )
        command_results.append(result)

        if not result["success"]:
            return _error_response(
                session_id=session_id,
                command_results=command_results,
                error_code="SRLINUX_CLIENT_RUNTIME_SETUP_FAILED",
                detail=f"Client runtime setup command failed: {command}",
            )

    verification_failure = _run_basic_link_verification(
        session_id=session_id,
        command_results=command_results,
        client_container=client_container,
        srl_container=srl_container,
    )

    if verification_failure is not None:
        return verification_failure

    fault_failure = _apply_srlinux_runtime_fault_injection(
        session=session,
        command_results=command_results,
    )

    if fault_failure is not None:
        return _error_response(
            session_id=session_id,
            command_results=command_results,
            error_code=fault_failure["error_code"],
            detail=fault_failure["detail"],
        )

    return _success_response(
        session_id=session_id,
        command_results=command_results,
        message="SR Linux runtime setup applied successfully.",
    )


def _run_basic_link_verification(
    *,
    session_id: str,
    command_results: list[dict[str, Any]],
    client_container: str,
    srl_container: str,
) -> dict[str, Any] | None:
    ping_retry_command = _ping_retry_command("10.10.10.1")

    verification_commands = [
        (
            "client1",
            client_container,
            ["sh", "-lc", "ip -4 addr show dev eth1"],
            "verify client1 eth1 IPv4 address",
            "10.10.10.10/24",
        ),
        (
            "client1",
            client_container,
            ["sh", "-lc", "ip route"],
            "verify client1 default route",
            "default via 10.10.10.1",
        ),
        (
            "srl1",
            srl_container,
            ["sr_cli", "-ec", "info from state interface ethernet-1/1 subinterface 0 ipv4"],
            "verify srl1 gateway address",
            "10.10.10.1/24",
        ),
        (
            "srl1",
            srl_container,
            ["sr_cli", "-ec", "info network-instance default"],
            "verify srl1 default network-instance binding",
            "interface ethernet-1/1.0",
        ),
        (
            "client1",
            client_container,
            ["sh", "-lc", ping_retry_command],
            "verify client1 can ping srl1 gateway",
            "bytes from 10.10.10.1",
        ),
    ]

    return _run_verification_commands(
        session_id=session_id,
        command_results=command_results,
        verification_commands=verification_commands,
    )



def _apply_branch_static_routing_runtime_setup(
    *,
    session: dict[str, Any],
    session_id: str,
) -> dict[str, Any]:
    command_results: list[dict[str, Any]] = []

    required_devices = [
        *BRANCH_CLIENTS.keys(),
        *BRANCH_SRL_INTERFACES.keys(),
    ]
    containers = {
        device: _container_name_for_device(session, device)
        for device in required_devices
    }
    missing_devices = [
        device
        for device, container_name in containers.items()
        if not container_name
    ]

    if missing_devices:
        return _error_response(
            session_id=session_id,
            command_results=[],
            error_code="SRLINUX_BRANCH_RUNTIME_METADATA_MISSING",
            detail=(
                "Could not resolve required branch container names for: "
                + ", ".join(sorted(missing_devices))
                + "."
            ),
        )

    for device, interfaces in BRANCH_SRL_INTERFACES.items():
        srl_config_script = _build_campus_srl_config_script(
            device=device,
            interfaces=interfaces,
            static_routes=BRANCH_STATIC_ROUTES.get(device, []),
        )
        result = _run_docker_exec(
            container_name=str(containers[device]),
            command=["sr_cli"],
            stage="srlinux_branch_golden_setup",
            device=device,
            display_command=f"apply branch golden SR Linux config on {device}",
            input_text=srl_config_script,
        )
        command_results.append(result)

        if not result["success"]:
            return _error_response(
                session_id=session_id,
                command_results=command_results,
                error_code="SRLINUX_BRANCH_GOLDEN_SRL_CONFIG_FAILED",
                detail=f"Could not apply branch golden SR Linux config on {device}.",
            )

    for device, config in BRANCH_CLIENTS.items():
        client_setup_commands = _client_setup_commands(
            interface=config["interface"],
            ip_address=config["ip_address"],
            default_gateway=config["default_gateway"],
        )

        for command in client_setup_commands:
            result = _run_docker_exec(
                container_name=str(containers[device]),
                command=["sh", "-lc", command],
                stage="branch_client_runtime_setup",
                device=device,
                display_command=command,
            )
            command_results.append(result)

            if not result["success"]:
                return _error_response(
                    session_id=session_id,
                    command_results=command_results,
                    error_code="SRLINUX_BRANCH_CLIENT_RUNTIME_SETUP_FAILED",
                    detail=f"Branch client runtime setup command failed on {device}: {command}",
                )

    verification_failure = _run_branch_golden_verification(
        session_id=session_id,
        command_results=command_results,
        containers={device: str(name) for device, name in containers.items()},
    )

    if verification_failure is not None:
        return verification_failure

    fault_failure = _apply_srlinux_runtime_fault_injection(
        session=session,
        command_results=command_results,
    )

    if fault_failure is not None:
        return _error_response(
            session_id=session_id,
            command_results=command_results,
            error_code=fault_failure["error_code"],
            detail=fault_failure["detail"],
        )

    has_runtime_faults = bool(_srlinux_faults_for_session(session))
    message = (
        "SR Linux branch static routing golden runtime setup and runtime fault injection applied successfully."
        if has_runtime_faults
        else "SR Linux branch static routing golden runtime setup applied successfully."
    )

    return _success_response(
        session_id=session_id,
        command_results=command_results,
        message=message,
    )


def _run_branch_golden_verification(
    *,
    session_id: str,
    command_results: list[dict[str, Any]],
    containers: dict[str, str],
) -> dict[str, Any] | None:
    verification_commands: list[tuple[str, str, list[str], str, str]] = []

    for device, config in BRANCH_CLIENTS.items():
        interface = config["interface"]
        verification_commands.extend(
            [
                (
                    device,
                    containers[device],
                    ["sh", "-lc", f"ip -4 addr show dev {interface}"],
                    f"verify {device} {interface} IPv4 address",
                    config["ip_address"],
                ),
                (
                    device,
                    containers[device],
                    ["sh", "-lc", "ip route"],
                    f"verify {device} default route",
                    f"default via {config['default_gateway']}",
                ),
            ]
        )

    for device, interfaces in BRANCH_SRL_INTERFACES.items():
        for item in interfaces:
            interface = item["interface"]
            ip_address = item["ip_address"]
            verification_commands.extend(
                [
                    (
                        device,
                        containers[device],
                        [
                            "sr_cli",
                            "-ec",
                            f"info from state interface {interface} subinterface 0 ipv4",
                        ],
                        f"verify {device} {interface}.0 IPv4 address",
                        ip_address,
                    ),
                    (
                        device,
                        containers[device],
                        ["sr_cli", "-ec", "info network-instance default"],
                        f"verify {device} default network-instance binding for {interface}.0",
                        f"interface {_subinterface_name(interface)}",
                    ),
                ]
            )

    for device, routes in BRANCH_STATIC_ROUTES.items():
        for route in routes:
            prefix = route["prefix"]
            verification_commands.append(
                (
                    device,
                    containers[device],
                    ["sr_cli", "-ec", f"info network-instance default static-routes route {prefix}"],
                    f"verify {device} static route {prefix}",
                    f"static-next-hop-group {route['group']}",
                )
            )

    verification_commands.extend(
        [
            (
                "client1",
                containers["client1"],
                ["sh", "-lc", _ping_retry_command(BRANCH_CLIENTS["client1"]["remote_peer"])],
                "verify client1 can ping client2",
                f"bytes from {BRANCH_CLIENTS['client1']['remote_peer']}",
            ),
            (
                "client2",
                containers["client2"],
                ["sh", "-lc", _ping_retry_command(BRANCH_CLIENTS["client2"]["remote_peer"])],
                "verify client2 can ping client1",
                f"bytes from {BRANCH_CLIENTS['client2']['remote_peer']}",
            ),
        ]
    )

    return _run_verification_commands(
        session_id=session_id,
        command_results=command_results,
        verification_commands=verification_commands,
    )


def _apply_campus_core_static_routing_runtime_setup(
    *,
    session: dict[str, Any],
    session_id: str,
) -> dict[str, Any]:
    command_results: list[dict[str, Any]] = []

    required_devices = [
        *CAMPUS_CLIENTS.keys(),
        *CAMPUS_SRL_INTERFACES.keys(),
    ]
    containers = {
        device: _container_name_for_device(session, device)
        for device in required_devices
    }
    missing_devices = [
        device
        for device, container_name in containers.items()
        if not container_name
    ]

    if missing_devices:
        return _error_response(
            session_id=session_id,
            command_results=[],
            error_code="SRLINUX_CAMPUS_RUNTIME_METADATA_MISSING",
            detail=(
                "Could not resolve required campus container names for: "
                + ", ".join(sorted(missing_devices))
                + "."
            ),
        )

    for device, interfaces in CAMPUS_SRL_INTERFACES.items():
        srl_config_script = _build_campus_srl_config_script(
            device=device,
            interfaces=interfaces,
            static_routes=CAMPUS_STATIC_ROUTES.get(device, []),
        )
        result = _run_docker_exec(
            container_name=str(containers[device]),
            command=["sr_cli"],
            stage="srlinux_campus_golden_setup",
            device=device,
            display_command=f"apply campus golden SR Linux config on {device}",
            input_text=srl_config_script,
        )
        command_results.append(result)

        if not result["success"]:
            return _error_response(
                session_id=session_id,
                command_results=command_results,
                error_code="SRLINUX_CAMPUS_GOLDEN_SRL_CONFIG_FAILED",
                detail=f"Could not apply campus golden SR Linux config on {device}.",
            )

    for device, config in CAMPUS_CLIENTS.items():
        client_setup_commands = _client_setup_commands(
            interface=config["interface"],
            ip_address=config["ip_address"],
            default_gateway=config["default_gateway"],
        )

        for command in client_setup_commands:
            result = _run_docker_exec(
                container_name=str(containers[device]),
                command=["sh", "-lc", command],
                stage="campus_client_runtime_setup",
                device=device,
                display_command=command,
            )
            command_results.append(result)

            if not result["success"]:
                return _error_response(
                    session_id=session_id,
                    command_results=command_results,
                    error_code="SRLINUX_CAMPUS_CLIENT_RUNTIME_SETUP_FAILED",
                    detail=f"Campus client runtime setup command failed on {device}: {command}",
                )

    verification_failure = _run_campus_golden_verification(
        session_id=session_id,
        command_results=command_results,
        containers={device: str(name) for device, name in containers.items()},
    )

    if verification_failure is not None:
        return verification_failure

    fault_failure = _apply_srlinux_runtime_fault_injection(
        session=session,
        command_results=command_results,
    )

    if fault_failure is not None:
        return _error_response(
            session_id=session_id,
            command_results=command_results,
            error_code=fault_failure["error_code"],
            detail=fault_failure["detail"],
        )

    has_runtime_faults = bool(_srlinux_faults_for_session(session))
    message = (
        "SR Linux campus golden runtime setup and runtime fault injection applied successfully."
        if has_runtime_faults
        else "SR Linux campus golden runtime setup applied successfully."
    )

    return _success_response(
        session_id=session_id,
        command_results=command_results,
        message=message,
    )


def _build_campus_srl_config_script(
    *,
    device: str,
    interfaces: list[dict[str, str]],
    static_routes: list[dict[str, Any]],
) -> str:
    lines = ["enter candidate"]

    for item in interfaces:
        interface = item["interface"]
        ip_address = item["ip_address"]
        subinterface = _subinterface_name(interface)

        lines.extend(
            [
                f"set interface {interface} admin-state enable",
                f"set interface {interface} subinterface 0 admin-state enable",
                f"set interface {interface} subinterface 0 ipv4 admin-state enable",
                f"set interface {interface} subinterface 0 ipv4 address {ip_address}",
                f"set network-instance default interface {subinterface}",
            ]
        )

    for route in static_routes:
        prefix = route["prefix"]
        next_hop = route["next_hop"]
        next_hop_id = route["next_hop_id"]
        group = route["group"]

        lines.extend(
            [
                f"set network-instance default static next-hop {next_hop_id} ip-address {next_hop}",
                f"set network-instance default static next-hop-group {group} next-hop {next_hop_id}",
                f"set network-instance default static-routes route {prefix} admin-state enable",
                f"set network-instance default static-routes route {prefix} metric 1",
                f"set network-instance default static-routes route {prefix} preference 5",
                f"set network-instance default static-routes route {prefix} static-next-hop-group {group}",
            ]
        )

    lines.extend(["commit now", "quit", ""])

    return "\n".join(lines)


def _client_setup_commands(
    *,
    interface: str,
    ip_address: str,
    default_gateway: str,
) -> list[str]:
    return [
        f"ip addr flush dev {interface} || true",
        f"ip addr add {ip_address} dev {interface}",
        f"ip link set {interface} up",
        f"ip route replace default via {default_gateway} dev {interface}",
    ]


def _run_campus_golden_verification(
    *,
    session_id: str,
    command_results: list[dict[str, Any]],
    containers: dict[str, str],
) -> dict[str, Any] | None:
    verification_commands: list[tuple[str, str, list[str], str, str]] = []

    for device, config in CAMPUS_CLIENTS.items():
        interface = config["interface"]
        verification_commands.extend(
            [
                (
                    device,
                    containers[device],
                    ["sh", "-lc", f"ip -4 addr show dev {interface}"],
                    f"verify {device} {interface} IPv4 address",
                    config["ip_address"],
                ),
                (
                    device,
                    containers[device],
                    ["sh", "-lc", "ip route"],
                    f"verify {device} default route",
                    f"default via {config['default_gateway']}",
                ),
            ]
        )

    for device, interfaces in CAMPUS_SRL_INTERFACES.items():
        for item in interfaces:
            interface = item["interface"]
            ip_address = item["ip_address"]
            verification_commands.extend(
                [
                    (
                        device,
                        containers[device],
                        [
                            "sr_cli",
                            "-ec",
                            f"info from state interface {interface} subinterface 0 ipv4",
                        ],
                        f"verify {device} {interface}.0 IPv4 address",
                        ip_address,
                    ),
                    (
                        device,
                        containers[device],
                        ["sr_cli", "-ec", "info network-instance default"],
                        f"verify {device} default network-instance binding for {interface}.0",
                        f"interface {_subinterface_name(interface)}",
                    ),
                ]
            )

    for device, routes in CAMPUS_STATIC_ROUTES.items():
        for route in routes:
            prefix = route["prefix"]
            verification_commands.append(
                (
                    device,
                    containers[device],
                    ["sr_cli", "-ec", f"info network-instance default static-routes route {prefix}"],
                    f"verify {device} static route {prefix}",
                    f"static-next-hop-group {route['group']}",
                )
            )

    verification_commands.extend(
        [
            (
                "client1",
                containers["client1"],
                ["sh", "-lc", _ping_retry_command(CAMPUS_CLIENTS["client1"]["remote_peer"])],
                "verify client1 can ping client2",
                f"bytes from {CAMPUS_CLIENTS['client1']['remote_peer']}",
            ),
            (
                "client2",
                containers["client2"],
                ["sh", "-lc", _ping_retry_command(CAMPUS_CLIENTS["client2"]["remote_peer"])],
                "verify client2 can ping client1",
                f"bytes from {CAMPUS_CLIENTS['client2']['remote_peer']}",
            ),
        ]
    )

    return _run_verification_commands(
        session_id=session_id,
        command_results=command_results,
        verification_commands=verification_commands,
    )


def _run_verification_commands(
    *,
    session_id: str,
    command_results: list[dict[str, Any]],
    verification_commands: list[tuple[str, str, list[str], str, str]],
) -> dict[str, Any] | None:
    for device, container_name, command, display_command, expected_output in verification_commands:
        result = _run_docker_exec(
            container_name=container_name,
            command=command,
            stage="srlinux_runtime_verification",
            device=device,
            display_command=display_command,
        )
        command_results.append(result)

        if not result["success"] or expected_output not in result.get("stdout", ""):
            return _error_response(
                session_id=session_id,
                command_results=command_results,
                error_code="SRLINUX_RUNTIME_VERIFICATION_FAILED",
                detail=(
                    f"Runtime verification failed for {device}: "
                    f"expected output '{expected_output}' while running '{display_command}'."
                ),
            )

    return None


def _subinterface_name(interface: str) -> str:
    return f"{interface}.0"


def _ping_retry_command(ip_address: str) -> str:
    return (
        "for i in 1 2 3 4 5; do "
        f"ping -c 3 -W 2 {ip_address} && exit 0; "
        "sleep 2; "
        "done; "
        f"ping -c 3 -W 2 {ip_address}"
    )


def _run_docker_exec(
    *,
    container_name: str,
    command: list[str],
    stage: str,
    device: str,
    display_command: str,
    input_text: str | None = None,
) -> dict[str, Any]:
    docker_command = ["docker", "exec"]

    if input_text is not None:
        docker_command.append("-i")

    docker_command.extend([container_name, *command])

    try:
        completed = subprocess.run(
            docker_command,
            input=input_text,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except FileNotFoundError as exc:
        return {
            "stage": stage,
            "device": device,
            "command": display_command,
            "success": False,
            "return_code": None,
            "stdout": "",
            "stderr": str(exc),
        }
    except PermissionError as exc:
        return {
            "stage": stage,
            "device": device,
            "command": display_command,
            "success": False,
            "return_code": None,
            "stdout": "",
            "stderr": str(exc),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "stage": stage,
            "device": device,
            "command": display_command,
            "success": False,
            "return_code": None,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "Command timed out.",
        }

    return {
        "stage": stage,
        "device": device,
        "command": display_command,
        "success": completed.returncode == 0,
        "return_code": completed.returncode,
        "stdout": completed.stdout or "",
        "stderr": completed.stderr or "",
    }


def _success_response(
    *,
    session_id: str,
    command_results: list[dict[str, Any]],
    message: str,
) -> dict[str, Any]:
    return {
        "success": True,
        "session_id": session_id,
        "status": SessionStatus.deployed,
        "message": message,
        "command": "docker exec SR Linux runtime setup commands",
        "return_code": 0,
        "stdout": _format_command_results(command_results, stream="stdout"),
        "stderr": _format_command_results(command_results, stream="stderr"),
        "error_code": None,
        "detail": None,
        "suggestion": None,
    }


def _error_response(
    *,
    session_id: str,
    command_results: list[dict[str, Any]],
    error_code: str,
    detail: str,
) -> dict[str, Any]:
    return {
        "success": False,
        "session_id": session_id,
        "status": SessionStatus.error,
        "message": "Containerlab deployed, but SR Linux runtime setup failed.",
        "command": "docker exec SR Linux runtime setup commands",
        "return_code": 1,
        "stdout": _format_command_results(command_results, stream="stdout"),
        "stderr": _format_command_results(command_results, stream="stderr"),
        "error_code": error_code,
        "detail": detail,
        "suggestion": (
            "Inspect SR Linux and client containers, then retry deployment. "
            "If resources remain, destroy the lab before creating a new session."
        ),
    }


def _format_command_results(command_results: list[dict[str, Any]], stream: str) -> str:
    lines: list[str] = []

    for item in command_results:
        value = str(item.get(stream) or "").strip()

        if not value:
            continue

        lines.append(
            "[{stage}] {device} {command}\n{value}".format(
                stage=item.get("stage"),
                device=item.get("device"),
                command=item.get("command"),
                value=value,
            )
        )

    return "\n\n".join(lines)


def _container_name_for_device(session: dict[str, Any], device: str) -> str | None:
    for entry in session.get("cli_access", []) or []:
        entry_device_id = _entry_value(entry, "device_id")
        entry_name = _entry_value(entry, "name")

        if entry_device_id == device or entry_name == device:
            container_name = _entry_value(entry, "container_name")
            if container_name:
                return str(container_name)

    lab_name = session.get("lab_name")
    if lab_name:
        return f"clab-{lab_name}-{device}"

    session_id = session.get("session_id")
    if session_id:
        return f"clab-autonetlab-{session_id}-{device}"

    return None


def _scenario_id(session: dict[str, Any]) -> str | None:
    scenario = session.get("scenario")

    if isinstance(scenario, dict):
        return scenario.get("id")

    return None


def _apply_srlinux_runtime_fault_injection(
    *,
    session: dict[str, Any],
    command_results: list[dict[str, Any]],
) -> dict[str, str] | None:
    faults = _srlinux_faults_for_session(session)

    for fault in faults:
        device = str(fault.get("device") or "")
        container_name = _container_name_for_device(session, device)

        if not container_name:
            return {
                "error_code": "SRLINUX_RUNTIME_FAULT_METADATA_MISSING",
                "detail": f"Could not resolve container name for SR Linux runtime fault device: {device}.",
            }

        commands = [
            str(command)
            for command in fault.get("injection_commands", [])
            if str(command).strip()
        ]

        if not commands:
            return {
                "error_code": "SRLINUX_RUNTIME_FAULT_COMMAND_MISSING",
                "detail": f"No runtime fault injection commands were defined for {fault.get('variant_id') or fault.get('code')}.",
            }

        for command in commands:
            result = _run_docker_exec(
                container_name=container_name,
                command=["sh", "-lc", command],
                stage="srlinux_runtime_fault_injection",
                device=device,
                display_command=command,
            )
            command_results.append(result)

            if not result["success"]:
                return {
                    "error_code": "SRLINUX_RUNTIME_FAULT_INJECTION_FAILED",
                    "detail": (
                        f"SR Linux runtime fault injection failed for {device}: "
                        f"{command}"
                    ),
                }

    return None


def _srlinux_faults_for_session(session: dict[str, Any]) -> list[dict[str, Any]]:
    faults: list[dict[str, Any]] = []

    for fault in _normalized_errors(session.get("injected_errors")):
        variant_id = str(fault.get("variant_id") or "")
        commands = [
            str(command)
            for command in fault.get("injection_commands", [])
            if str(command).strip()
        ]

        if variant_id and commands:
            faults.append(fault)

    return faults


def _normalized_errors(errors: Any) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []

    for error in errors or []:
        if hasattr(error, "model_dump"):
            normalized.append(error.model_dump())
        elif isinstance(error, dict):
            normalized.append(error)

    return normalized


def _entry_value(entry: Any, key: str) -> Any:
    if isinstance(entry, dict):
        return entry.get(key)

    return getattr(entry, key, None)
