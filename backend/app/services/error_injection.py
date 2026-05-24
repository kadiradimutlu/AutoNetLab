import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

from app.schemas.enums import Difficulty
from app.schemas.lab import ErrorItem


ERROR_COUNT_BY_DIFFICULTY = {
    Difficulty.easy: 2,
    Difficulty.medium: 3,
    Difficulty.hard: 5,
}


ERROR_TAXONOMY = [
    "ip_addressing",
    "subnetting",
    "interface_status",
    "default_gateway",
    "static_routing",
    "vlan_like",
    "acl_like",
    "connectivity",
]


BASE_CONFIG_BY_DEVICE = {
    "r1": [
        "# AutoNetLab generated config for r1",
        "hostname r1",
        "interface eth1 ip address 10.10.12.1/24",
        "interface eth2 ip address 10.10.14.1/24",
        "ip route 10.10.23.0/24 via 10.10.12.2",
        "ip route 10.10.34.0/24 via 10.10.14.2",
    ],
    "r2": [
        "# AutoNetLab generated config for r2",
        "hostname r2",
        "interface eth1 ip address 10.10.12.2/24",
        "interface eth2 ip address 10.10.23.1/24",
        "ip route 0.0.0.0/0 via 10.10.12.1",
        "ip route 10.10.14.0/24 via 10.10.12.1",
        "ip route 10.10.34.0/24 via 10.10.23.2",
    ],
    "r3": [
        "# AutoNetLab generated config for r3",
        "hostname r3",
        "interface eth1 ip address 10.10.23.2/24",
        "interface eth2 ip address 10.10.34.1/24",
        "ip route 10.10.12.0/24 via 10.10.23.1",
        "ip route 10.10.14.0/24 via 10.10.34.2",
    ],
    "r4": [
        "# AutoNetLab generated config for r4",
        "hostname r4",
        "interface eth1 ip address 10.10.34.2/24",
        "interface eth2 ip address 10.10.14.2/24",
        "ip route 0.0.0.0/0 via 10.10.34.1",
        "ip route 10.10.23.0/24 via 10.10.34.1",
        "ip route 10.10.12.0/24 via 10.10.14.1",
    ],
}


def _scenario(
    *,
    code: str,
    topic: str,
    device: str,
    description: str,
    severity: str,
    variant_id: str,
    config_line: str,
    injection_commands: list[str],
    validation_command: str,
    expected_outputs: list[str],
    interface: str | None = None,
    required_devices: list[str] | None = None,
    conflict_key: str | None = None,
) -> dict[str, Any]:
    return {
        "code": code,
        "topic": topic,
        "device": device,
        "description": description,
        "severity": severity,
        "variant_id": variant_id,
        "interface": interface,
        "config_line": config_line,
        "injection_commands": injection_commands,
        "validation_command": validation_command,
        "expected_outputs": expected_outputs,
        "required_devices": required_devices or [device],
        "conflict_key": conflict_key or f"{device}:{topic}:{interface or variant_id}",
    }


ERROR_POOL = [
    # IP addressing variants
    _scenario(
        code="IP_ADDRESS_MISMATCH",
        topic="ip_addressing",
        device="r1",
        interface="eth1",
        severity="low",
        variant_id="r1_eth1_wrong_host_ip",
        description="Incorrect host IP configured on r1 eth1.",
        config_line="interface eth1 ip address 10.10.10.99/24  # IP_ADDRESS_MISMATCH",
        injection_commands=[
            "ip addr flush dev eth1",
            "ip addr add 10.10.10.99/24 dev eth1",
            "ip link set eth1 up",
        ],
        validation_command="ip addr show eth1",
        expected_outputs=["inet 10.10.12.1/24"],
        required_devices=["r1", "r2"],
        conflict_key="r1:eth1:addressing",
    ),
    _scenario(
        code="IP_ADDRESS_R2_ETH2_WRONG_SUBNET",
        topic="ip_addressing",
        device="r2",
        interface="eth2",
        severity="medium",
        variant_id="r2_eth2_wrong_subnet_ip",
        description="r2 eth2 is configured with an IP address from the wrong subnet.",
        config_line="interface eth2 ip address 10.10.99.1/24  # IP_ADDRESS_R2_ETH2_WRONG_SUBNET",
        injection_commands=[
            "ip addr flush dev eth2",
            "ip addr add 10.10.99.1/24 dev eth2",
            "ip link set eth2 up",
        ],
        validation_command="ip addr show eth2",
        expected_outputs=["inet 10.10.23.1/24"],
        required_devices=["r2", "r3"],
        conflict_key="r2:eth2:addressing",
    ),
    _scenario(
        code="IP_ADDRESS_R3_ETH1_DUPLICATE",
        topic="ip_addressing",
        device="r3",
        interface="eth1",
        severity="medium",
        variant_id="r3_eth1_duplicate_peer_ip",
        description="r3 eth1 uses the same IP address as its r2-side peer.",
        config_line="interface eth1 ip address 10.10.23.1/24  # IP_ADDRESS_R3_ETH1_DUPLICATE",
        injection_commands=[
            "ip addr flush dev eth1",
            "ip addr add 10.10.23.1/24 dev eth1",
            "ip link set eth1 up",
        ],
        validation_command="ip addr show eth1",
        expected_outputs=["inet 10.10.23.2/24"],
        required_devices=["r2", "r3"],
        conflict_key="r3:eth1:addressing",
    ),
    _scenario(
        code="IP_ADDRESS_R4_ETH2_WRONG_HOST",
        topic="ip_addressing",
        device="r4",
        interface="eth2",
        severity="medium",
        variant_id="r4_eth2_wrong_host_ip",
        description="r4 eth2 has an incorrect host address on the r1-r4 link.",
        config_line="interface eth2 ip address 10.10.14.99/24  # IP_ADDRESS_R4_ETH2_WRONG_HOST",
        injection_commands=[
            "ip addr flush dev eth2",
            "ip addr add 10.10.14.99/24 dev eth2",
            "ip link set eth2 up",
        ],
        validation_command="ip addr show eth2",
        expected_outputs=["inet 10.10.14.2/24"],
        required_devices=["r1", "r4"],
        conflict_key="r4:eth2:addressing",
    ),

    # Subnetting variants
    _scenario(
        code="WRONG_SUBNET_MASK_R1",
        topic="subnetting",
        device="r1",
        interface="eth1",
        severity="medium",
        variant_id="r1_eth1_mask_too_wide",
        description="r1 eth1 uses an incorrect subnet mask.",
        config_line="interface eth1 ip address 10.10.12.1/16  # WRONG_SUBNET_MASK_R1",
        injection_commands=[
            "ip addr flush dev eth1",
            "ip addr add 10.10.12.1/16 dev eth1",
            "ip link set eth1 up",
        ],
        validation_command="ip addr show eth1",
        expected_outputs=["inet 10.10.12.1/24"],
        required_devices=["r1", "r2"],
        conflict_key="r1:eth1:addressing",
    ),
    _scenario(
        code="WRONG_SUBNET_MASK_R2_ETH2",
        topic="subnetting",
        device="r2",
        interface="eth2",
        severity="medium",
        variant_id="r2_eth2_mask_too_wide",
        description="r2 eth2 uses an incorrect subnet mask.",
        config_line="interface eth2 ip address 10.10.23.1/16  # WRONG_SUBNET_MASK_R2_ETH2",
        injection_commands=[
            "ip addr flush dev eth2",
            "ip addr add 10.10.23.1/16 dev eth2",
            "ip link set eth2 up",
        ],
        validation_command="ip addr show eth2",
        expected_outputs=["inet 10.10.23.1/24"],
        required_devices=["r2", "r3"],
        conflict_key="r2:eth2:addressing",
    ),
    _scenario(
        code="WRONG_SUBNET_MASK",
        topic="subnetting",
        device="r3",
        interface="eth1",
        severity="low",
        variant_id="r3_eth1_mask_too_wide",
        description="r3 eth1 uses an incorrect subnet mask.",
        config_line="interface eth1 ip address 10.10.23.2/16  # WRONG_SUBNET_MASK",
        injection_commands=[
            "ip addr flush dev eth1",
            "ip addr add 10.10.23.2/16 dev eth1",
            "ip link set eth1 up",
        ],
        validation_command="ip addr show eth1",
        expected_outputs=["inet 10.10.23.2/24"],
        required_devices=["r2", "r3"],
        conflict_key="r3:eth1:addressing",
    ),
    _scenario(
        code="WRONG_SUBNET_MASK_R4_ETH1",
        topic="subnetting",
        device="r4",
        interface="eth1",
        severity="medium",
        variant_id="r4_eth1_mask_too_narrow",
        description="r4 eth1 uses an incompatible subnet mask.",
        config_line="interface eth1 ip address 10.10.34.2/30  # WRONG_SUBNET_MASK_R4_ETH1",
        injection_commands=[
            "ip addr flush dev eth1",
            "ip addr add 10.10.34.2/30 dev eth1",
            "ip link set eth1 up",
        ],
        validation_command="ip addr show eth1",
        expected_outputs=["inet 10.10.34.2/24"],
        required_devices=["r3", "r4"],
        conflict_key="r4:eth1:addressing",
    ),

    # Interface status variants
    _scenario(
        code="INTERFACE_DOWN_R1_ETH2",
        topic="interface_status",
        device="r1",
        interface="eth2",
        severity="medium",
        variant_id="r1_eth2_shutdown",
        description="r1 eth2 is administratively down.",
        config_line="interface eth2 shutdown  # INTERFACE_DOWN_R1_ETH2",
        injection_commands=["ip link set eth2 down"],
        validation_command="ip link show eth2",
        expected_outputs=["state UP"],
        required_devices=["r1", "r4"],
        conflict_key="r1:eth2:link_state",
    ),
    _scenario(
        code="INTERFACE_DOWN_R2",
        topic="interface_status",
        device="r2",
        interface="eth1",
        severity="medium",
        variant_id="r2_eth1_shutdown",
        description="r2 eth1 is administratively down.",
        config_line="interface eth1 shutdown  # INTERFACE_DOWN_R2",
        injection_commands=["ip link set eth1 down"],
        validation_command="ip link show eth1",
        expected_outputs=["state UP"],
        required_devices=["r1", "r2"],
        conflict_key="r2:eth1:link_state",
    ),
    _scenario(
        code="INTERFACE_DOWN_R3_ETH2",
        topic="interface_status",
        device="r3",
        interface="eth2",
        severity="high",
        variant_id="r3_eth2_shutdown",
        description="r3 eth2 is administratively down.",
        config_line="interface eth2 shutdown  # INTERFACE_DOWN_R3_ETH2",
        injection_commands=["ip link set eth2 down"],
        validation_command="ip link show eth2",
        expected_outputs=["state UP"],
        required_devices=["r3", "r4"],
        conflict_key="r3:eth2:link_state",
    ),
    _scenario(
        code="INTERFACE_DOWN_R4",
        topic="interface_status",
        device="r4",
        interface="eth1",
        severity="high",
        variant_id="r4_eth1_shutdown",
        description="r4 eth1 is administratively down.",
        config_line="interface eth1 shutdown  # INTERFACE_DOWN_R4",
        injection_commands=["ip link set eth1 down"],
        validation_command="ip link show eth1",
        expected_outputs=["state UP"],
        required_devices=["r3", "r4"],
        conflict_key="r4:eth1:link_state",
    ),

    # Default gateway variants
    _scenario(
        code="WRONG_GATEWAY",
        topic="default_gateway",
        device="r2",
        severity="medium",
        variant_id="r2_default_gateway_nonexistent_peer",
        description="r2 has an incorrect default gateway.",
        config_line="ip route 0.0.0.0/0 via 10.10.12.254  # WRONG_GATEWAY",
        injection_commands=["ip route replace default via 10.10.12.254"],
        validation_command="ip route",
        expected_outputs=["default via 10.10.12.1"],
        required_devices=["r1", "r2"],
        conflict_key="r2:default_route",
    ),
    _scenario(
        code="WRONG_GATEWAY_R2_SELF",
        topic="default_gateway",
        device="r2",
        severity="high",
        variant_id="r2_default_gateway_points_to_self",
        description="r2 default gateway points to itself instead of r1.",
        config_line="ip route 0.0.0.0/0 via 10.10.12.2  # WRONG_GATEWAY_R2_SELF",
        injection_commands=["ip route replace default via 10.10.12.2"],
        validation_command="ip route",
        expected_outputs=["default via 10.10.12.1"],
        required_devices=["r1", "r2"],
        conflict_key="r2:default_route",
    ),
    _scenario(
        code="WRONG_GATEWAY_R4",
        topic="default_gateway",
        device="r4",
        severity="high",
        variant_id="r4_default_gateway_nonexistent_peer",
        description="r4 has an incorrect default gateway.",
        config_line="ip route 0.0.0.0/0 via 10.10.34.254  # WRONG_GATEWAY_R4",
        injection_commands=["ip route replace default via 10.10.34.254"],
        validation_command="ip route",
        expected_outputs=["default via 10.10.34.1"],
        required_devices=["r3", "r4"],
        conflict_key="r4:default_route",
    ),
    _scenario(
        code="WRONG_GATEWAY_R4_BACKUP_SIDE",
        topic="default_gateway",
        device="r4",
        severity="high",
        variant_id="r4_default_gateway_uses_backup_link",
        description="r4 default gateway incorrectly points toward the r1-r4 backup link.",
        config_line="ip route 0.0.0.0/0 via 10.10.14.1  # WRONG_GATEWAY_R4_BACKUP_SIDE",
        injection_commands=["ip route replace default via 10.10.14.1"],
        validation_command="ip route",
        expected_outputs=["default via 10.10.34.1"],
        required_devices=["r1", "r3", "r4"],
        conflict_key="r4:default_route",
    ),

    # Static routing variants
    _scenario(
        code="MISSING_ROUTE_R1_TO_R3",
        topic="static_routing",
        device="r1",
        severity="medium",
        variant_id="r1_missing_route_to_r2_r3_network",
        description="r1 is missing the static route toward the r2-r3 network.",
        config_line="no ip route 10.10.23.0/24 via 10.10.12.2  # MISSING_ROUTE_R1_TO_R3",
        injection_commands=["ip route del 10.10.23.0/24 || true"],
        validation_command="ip route",
        expected_outputs=["10.10.23.0/24 via 10.10.12.2"],
        required_devices=["r1", "r2", "r3"],
        conflict_key="r1:route:10.10.23.0/24",
    ),
    _scenario(
        code="MISSING_ROUTE",
        topic="static_routing",
        device="r2",
        severity="medium",
        variant_id="r2_missing_route_to_r3_r4_network",
        description="r2 is missing the static route toward the r3-r4 network.",
        config_line="no ip route 10.10.34.0/24 via 10.10.23.2  # MISSING_ROUTE",
        injection_commands=["ip route del 10.10.34.0/24 || true"],
        validation_command="ip route",
        expected_outputs=["10.10.34.0/24 via 10.10.23.2"],
        required_devices=["r2", "r3", "r4"],
        conflict_key="r2:route:10.10.34.0/24",
    ),
    _scenario(
        code="MISSING_ROUTE_R3",
        topic="static_routing",
        device="r3",
        severity="medium",
        variant_id="r3_missing_route_to_r1_r2_network",
        description="r3 is missing the static route toward the r1-r2 network.",
        config_line="no ip route 10.10.12.0/24 via 10.10.23.1  # MISSING_ROUTE_R3",
        injection_commands=["ip route del 10.10.12.0/24 || true"],
        validation_command="ip route",
        expected_outputs=["10.10.12.0/24 via 10.10.23.1"],
        required_devices=["r1", "r2", "r3"],
        conflict_key="r3:route:10.10.12.0/24",
    ),
    _scenario(
        code="MISSING_ROUTE_R4_TO_R1",
        topic="static_routing",
        device="r4",
        severity="medium",
        variant_id="r4_missing_route_to_r1_r2_network",
        description="r4 is missing the static route toward the r1-r2 network.",
        config_line="no ip route 10.10.12.0/24 via 10.10.14.1  # MISSING_ROUTE_R4_TO_R1",
        injection_commands=["ip route del 10.10.12.0/24 || true"],
        validation_command="ip route",
        expected_outputs=["10.10.12.0/24 via 10.10.14.1"],
        required_devices=["r1", "r4"],
        conflict_key="r4:route:10.10.12.0/24",
    ),
    _scenario(
        code="WRONG_ROUTE_R1_TO_R4",
        topic="static_routing",
        device="r1",
        severity="high",
        variant_id="r1_wrong_next_hop_to_r3_r4_network",
        description="r1 uses the wrong next-hop for the r3-r4 network.",
        config_line="ip route 10.10.34.0/24 via 10.10.12.254  # WRONG_ROUTE_R1_TO_R4",
        injection_commands=["ip route replace 10.10.34.0/24 via 10.10.12.254"],
        validation_command="ip route",
        expected_outputs=["10.10.34.0/24 via 10.10.14.2"],
        required_devices=["r1", "r2", "r4"],
        conflict_key="r1:route:10.10.34.0/24",
    ),
    _scenario(
        code="WRONG_ROUTE_R3_TO_R1",
        topic="static_routing",
        device="r3",
        severity="high",
        variant_id="r3_wrong_next_hop_to_r1_r2_network",
        description="r3 uses the wrong next-hop for the r1-r2 network.",
        config_line="ip route 10.10.12.0/24 via 10.10.34.254  # WRONG_ROUTE_R3_TO_R1",
        injection_commands=["ip route replace 10.10.12.0/24 via 10.10.34.254"],
        validation_command="ip route",
        expected_outputs=["10.10.12.0/24 via 10.10.23.1"],
        required_devices=["r1", "r2", "r3", "r4"],
        conflict_key="r3:route:10.10.12.0/24",
    ),

    # VLAN-like / link-side mismatch variants
    _scenario(
        code="VLAN_MISMATCH",
        topic="vlan_like",
        device="r1",
        interface="eth2",
        severity="medium",
        variant_id="r1_eth2_wrong_link_subnet",
        description="r1 eth2 is placed into a wrong link-side subnet.",
        config_line="interface eth2 vlan 999  # VLAN_MISMATCH",
        injection_commands=[
            "ip addr flush dev eth2",
            "ip addr add 10.10.140.1/24 dev eth2",
            "ip link set eth2 up",
        ],
        validation_command="ip addr show eth2",
        expected_outputs=["inet 10.10.14.1/24"],
        required_devices=["r1", "r4"],
        conflict_key="r1:eth2:addressing",
    ),
    _scenario(
        code="VLAN_MISMATCH_R2_R3",
        topic="vlan_like",
        device="r2",
        interface="eth2",
        severity="medium",
        variant_id="r2_eth2_wrong_link_subnet",
        description="r2 eth2 is placed into a wrong link-side subnet.",
        config_line="interface eth2 vlan 230  # VLAN_MISMATCH_R2_R3",
        injection_commands=[
            "ip addr flush dev eth2",
            "ip addr add 10.10.24.1/24 dev eth2",
            "ip link set eth2 up",
        ],
        validation_command="ip addr show eth2",
        expected_outputs=["inet 10.10.23.1/24"],
        required_devices=["r2", "r3"],
        conflict_key="r2:eth2:addressing",
    ),
    _scenario(
        code="VLAN_MISMATCH_R3",
        topic="vlan_like",
        device="r3",
        interface="eth2",
        severity="medium",
        variant_id="r3_eth2_wrong_link_subnet",
        description="r3 eth2 is placed into a wrong link-side subnet.",
        config_line="interface eth2 vlan 300  # VLAN_MISMATCH_R3",
        injection_commands=[
            "ip addr flush dev eth2",
            "ip addr add 10.10.35.1/24 dev eth2",
            "ip link set eth2 up",
        ],
        validation_command="ip addr show eth2",
        expected_outputs=["inet 10.10.34.1/24"],
        required_devices=["r3", "r4"],
        conflict_key="r3:eth2:addressing",
    ),
    _scenario(
        code="VLAN_MISMATCH_R4_BACKUP",
        topic="vlan_like",
        device="r4",
        interface="eth2",
        severity="medium",
        variant_id="r4_eth2_wrong_link_subnet",
        description="r4 eth2 is placed into a wrong link-side subnet.",
        config_line="interface eth2 vlan 414  # VLAN_MISMATCH_R4_BACKUP",
        injection_commands=[
            "ip addr flush dev eth2",
            "ip addr add 10.10.140.2/24 dev eth2",
            "ip link set eth2 up",
        ],
        validation_command="ip addr show eth2",
        expected_outputs=["inet 10.10.14.2/24"],
        required_devices=["r1", "r4"],
        conflict_key="r4:eth2:addressing",
    ),

    # ACL-like policy variants implemented as route-level policy simulation
    _scenario(
        code="ACL_BLOCK_ICMP_R1",
        topic="acl_like",
        device="r1",
        severity="high",
        variant_id="r1_policy_blocks_icmp_to_r2",
        description="A policy-like host route blocks ICMP troubleshooting traffic from r1 to r2.",
        config_line="access-list AUTONETLAB-DEMO deny icmp host r1 host r2  # ACL_BLOCK_ICMP_R1",
        injection_commands=["ip route replace 10.10.12.2/32 via 10.10.14.254"],
        validation_command="ping -c 1 -W 1 10.10.12.2",
        expected_outputs=["1 packets received"],
        required_devices=["r1", "r2", "r4"],
        conflict_key="r1:host_policy:10.10.12.2",
    ),
    _scenario(
        code="ACL_BLOCK_ICMP_R3",
        topic="acl_like",
        device="r3",
        severity="high",
        variant_id="r3_policy_blocks_icmp_to_r2",
        description="A policy-like host route blocks ICMP troubleshooting traffic from r3 to r2.",
        config_line="access-list AUTONETLAB-DEMO deny icmp host r3 host r2  # ACL_BLOCK_ICMP_R3",
        injection_commands=["ip route replace 10.10.23.1/32 via 10.10.34.254"],
        validation_command="ping -c 1 -W 1 10.10.23.1",
        expected_outputs=["1 packets received"],
        required_devices=["r2", "r3", "r4"],
        conflict_key="r3:host_policy:10.10.23.1",
    ),
    _scenario(
        code="ACL_BLOCK_ICMP_R4_TO_R1",
        topic="acl_like",
        device="r4",
        severity="high",
        variant_id="r4_policy_blocks_icmp_to_r1",
        description="A policy-like host route blocks ICMP troubleshooting traffic from r4 to r1.",
        config_line="access-list AUTONETLAB-DEMO deny icmp host r4 host r1  # ACL_BLOCK_ICMP_R4_TO_R1",
        injection_commands=["ip route replace 10.10.14.1/32 via 10.10.34.254"],
        validation_command="ping -c 1 -W 1 10.10.14.1",
        expected_outputs=["1 packets received"],
        required_devices=["r1", "r3", "r4"],
        conflict_key="r4:host_policy:10.10.14.1",
    ),

    # Connectivity variants
    _scenario(
        code="CONNECTIVITY_FAILURE_R2_R3",
        topic="connectivity",
        device="r2",
        interface="eth2",
        severity="high",
        variant_id="r2_r3_link_wrong_subnet",
        description="Connectivity between r2 and r3 is broken by an incorrect r2-side link setting.",
        config_line="interface eth2 connectivity-check failed  # CONNECTIVITY_FAILURE_R2_R3",
        injection_commands=[
            "ip addr flush dev eth2",
            "ip addr add 10.10.99.1/24 dev eth2",
            "ip link set eth2 up",
        ],
        validation_command="ping -c 1 -W 1 10.10.23.2",
        expected_outputs=["1 packets received"],
        required_devices=["r2", "r3"],
        conflict_key="r2:eth2:addressing",
    ),
    _scenario(
        code="CONNECTIVITY_FAILURE_R1_R4",
        topic="connectivity",
        device="r4",
        interface="eth2",
        severity="high",
        variant_id="r1_r4_backup_link_wrong_subnet",
        description="Backup connectivity between r1 and r4 is broken by an incorrect r4-side link setting.",
        config_line="interface eth2 connectivity-check failed  # CONNECTIVITY_FAILURE_R1_R4",
        injection_commands=[
            "ip addr flush dev eth2",
            "ip addr add 10.10.99.4/24 dev eth2",
            "ip link set eth2 up",
        ],
        validation_command="ping -c 1 -W 1 10.10.14.1",
        expected_outputs=["1 packets received"],
        required_devices=["r1", "r4"],
        conflict_key="r4:eth2:addressing",
    ),
    _scenario(
        code="CONNECTIVITY_FAILURE_R3_R4",
        topic="connectivity",
        device="r3",
        interface="eth2",
        severity="high",
        variant_id="r3_r4_link_wrong_subnet",
        description="Connectivity between r3 and r4 is broken by an incorrect r3-side link setting.",
        config_line="interface eth2 connectivity-check failed  # CONNECTIVITY_FAILURE_R3_R4",
        injection_commands=[
            "ip addr flush dev eth2",
            "ip addr add 10.10.88.1/24 dev eth2",
            "ip link set eth2 up",
        ],
        validation_command="ping -c 1 -W 1 10.10.34.2",
        expected_outputs=["1 packets received"],
        required_devices=["r3", "r4"],
        conflict_key="r3:eth2:addressing",
    ),
]


def generate_errors(
    difficulty: Difficulty,
    seed: str,
    topology_devices: list[str] | None = None,
) -> list[ErrorItem]:
    selected_errors = _select_errors(
        difficulty=difficulty,
        seed=seed,
        topology_devices=topology_devices,
    )

    return [
        _to_error_item(error)
        for error in selected_errors
    ]


def apply_error_injection(
    difficulty: Difficulty,
    seed: str,
    session_dir: Path,
    topology_devices: list[str] | None = None,
) -> list[ErrorItem]:
    selected_errors = _select_errors(
        difficulty=difficulty,
        seed=seed,
        topology_devices=topology_devices,
    )

    error_items = [
        _to_error_item(error)
        for error in selected_errors
    ]

    configs_dir = session_dir / "configs"
    errors_dir = session_dir / "errors"

    configs_dir.mkdir(parents=True, exist_ok=True)
    errors_dir.mkdir(parents=True, exist_ok=True)

    _write_device_configs(
        configs_dir=configs_dir,
        selected_errors=selected_errors,
        topology_devices=topology_devices,
    )

    _write_error_metadata(
        errors_dir=errors_dir,
        error_items=error_items,
        difficulty=difficulty,
        seed=seed,
        topology_devices=topology_devices,
    )

    return error_items


def _to_error_item(error: dict[str, Any]) -> ErrorItem:
    return ErrorItem(
        code=error["code"],
        topic=error["topic"],
        device=error["device"],
        description=error["description"],
        severity=error["severity"],
        variant_id=error.get("variant_id"),
        interface=error.get("interface"),
        validation_command=error.get("validation_command"),
        expected_outputs=list(error.get("expected_outputs", [])),
        injection_commands=list(error.get("injection_commands", [])),
    )


def _select_errors(
    difficulty: Difficulty,
    seed: str,
    topology_devices: list[str] | None = None,
) -> list[dict[str, Any]]:
    count = ERROR_COUNT_BY_DIFFICULTY[difficulty]
    randomizer = random.Random(seed)

    available_errors = _available_errors_for_topology(topology_devices)

    if not available_errors:
        return []

    if count > len(available_errors):
        count = len(available_errors)

    if difficulty == Difficulty.hard:
        return _select_diverse_hard_errors(
            available_errors=available_errors,
            count=count,
            randomizer=randomizer,
        )

    shuffled_errors = list(available_errors)
    randomizer.shuffle(shuffled_errors)

    return _take_without_conflicts(
        candidates=shuffled_errors,
        count=count,
    )


def _available_errors_for_topology(topology_devices: list[str] | None = None) -> list[dict[str, Any]]:
    allowed_devices = set(topology_devices or [])

    if not allowed_devices:
        return list(ERROR_POOL)

    return [
        error
        for error in ERROR_POOL
        if set(error.get("required_devices", [error["device"]])) <= allowed_devices
    ]


def _select_diverse_hard_errors(
    available_errors: list[dict[str, Any]],
    count: int,
    randomizer: random.Random,
) -> list[dict[str, Any]]:
    selected_errors: list[dict[str, Any]] = []
    selected_codes: set[str] = set()
    selected_conflicts: set[str] = set()

    available_devices = sorted(
        {
            str(error["device"])
            for error in available_errors
            if error.get("device")
        }
    )
    randomizer.shuffle(available_devices)

    minimum_device_count = min(3, count, len(available_devices))

    for device in available_devices:
        if len(selected_errors) >= minimum_device_count:
            break

        device_candidates = [
            error
            for error in available_errors
            if error.get("device") == device
            and _can_select_error(error, selected_codes, selected_conflicts)
        ]

        if not device_candidates:
            continue

        selected_error = randomizer.choice(device_candidates)
        _add_selected_error(
            selected_errors=selected_errors,
            selected_codes=selected_codes,
            selected_conflicts=selected_conflicts,
            error=selected_error,
        )

    errors_by_topic: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for error in available_errors:
        if _can_select_error(error, selected_codes, selected_conflicts):
            errors_by_topic[error["topic"]].append(error)

    topics = list(errors_by_topic.keys())
    randomizer.shuffle(topics)

    selected_topics = {
        error["topic"]
        for error in selected_errors
    }

    for topic in topics:
        if len(selected_errors) >= count:
            break

        if topic in selected_topics and len(selected_topics) < len(topics):
            continue

        topic_candidates = [
            error
            for error in errors_by_topic[topic]
            if _can_select_error(error, selected_codes, selected_conflicts)
        ]

        if not topic_candidates:
            continue

        selected_error = randomizer.choice(topic_candidates)
        _add_selected_error(
            selected_errors=selected_errors,
            selected_codes=selected_codes,
            selected_conflicts=selected_conflicts,
            error=selected_error,
        )
        selected_topics.add(topic)

    remaining_errors = list(available_errors)
    randomizer.shuffle(remaining_errors)

    for error in remaining_errors:
        if len(selected_errors) >= count:
            break

        if not _can_select_error(error, selected_codes, selected_conflicts):
            continue

        _add_selected_error(
            selected_errors=selected_errors,
            selected_codes=selected_codes,
            selected_conflicts=selected_conflicts,
            error=error,
        )

    return selected_errors


def _take_without_conflicts(
    candidates: list[dict[str, Any]],
    count: int,
) -> list[dict[str, Any]]:
    selected_errors: list[dict[str, Any]] = []
    selected_codes: set[str] = set()
    selected_conflicts: set[str] = set()

    for error in candidates:
        if len(selected_errors) >= count:
            break

        if not _can_select_error(error, selected_codes, selected_conflicts):
            continue

        _add_selected_error(
            selected_errors=selected_errors,
            selected_codes=selected_codes,
            selected_conflicts=selected_conflicts,
            error=error,
        )

    return selected_errors


def _can_select_error(
    error: dict[str, Any],
    selected_codes: set[str],
    selected_conflicts: set[str],
) -> bool:
    if error["code"] in selected_codes:
        return False

    conflict_key = str(error.get("conflict_key") or "")

    return not conflict_key or conflict_key not in selected_conflicts


def _add_selected_error(
    selected_errors: list[dict[str, Any]],
    selected_codes: set[str],
    selected_conflicts: set[str],
    error: dict[str, Any],
) -> None:
    selected_errors.append(error)
    selected_codes.add(error["code"])

    conflict_key = error.get("conflict_key")
    if conflict_key:
        selected_conflicts.add(str(conflict_key))


def _write_device_configs(
    configs_dir: Path,
    selected_errors: list[dict[str, Any]],
    topology_devices: list[str] | None = None,
) -> None:
    devices_to_write = list(topology_devices or BASE_CONFIG_BY_DEVICE.keys())

    config_by_device = {}

    for device in devices_to_write:
        config_by_device[device] = list(
            BASE_CONFIG_BY_DEVICE.get(
                device,
                [
                    f"# AutoNetLab generated config for {device}",
                    f"hostname {device}",
                ],
            )
        )

    for error in selected_errors:
        device = error["device"]

        if device not in config_by_device:
            config_by_device[device] = [
                f"# AutoNetLab generated config for {device}",
                f"hostname {device}",
            ]

        config_by_device[device].append("")
        config_by_device[device].append("# Injected error")
        config_by_device[device].append(f"# {error['code']}: {error['description']}")
        config_by_device[device].append(f"# variant_id: {error['variant_id']}")
        config_by_device[device].append(error["config_line"])

    for device, lines in config_by_device.items():
        config_path = configs_dir / f"{device}.conf"
        config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_error_metadata(
    errors_dir: Path,
    error_items: list[ErrorItem],
    difficulty: Difficulty,
    seed: str,
    topology_devices: list[str] | None = None,
) -> None:
    metadata_path = errors_dir / "injected_errors.json"

    payload = {
        "difficulty": difficulty.value,
        "seed": seed,
        "topology_devices": topology_devices or [],
        "error_taxonomy": ERROR_TAXONOMY,
        "error_scenario_count": len(ERROR_POOL),
        "injected_errors": [
            error.model_dump()
            for error in error_items
        ],
    }

    metadata_path.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )
