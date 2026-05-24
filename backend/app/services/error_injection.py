import json
import random
from collections import defaultdict
from pathlib import Path

from app.schemas.enums import Difficulty
from app.schemas.lab import ErrorItem


ERROR_POOL = [
    {
        "code": "IP_ADDRESS_MISMATCH",
        "topic": "ip_addressing",
        "device": "r1",
        "description": "Incorrect IP address configured on r1 eth1.",
        "severity": "low",
        "config_line": "interface eth1 ip address 10.10.10.99/24  # IP_ADDRESS_MISMATCH",
    },
    {
        "code": "WRONG_SUBNET_MASK_R1",
        "topic": "subnetting",
        "device": "r1",
        "description": "Wrong subnet mask configured on r1 eth1.",
        "severity": "medium",
        "config_line": "interface eth1 ip address 10.10.12.1/16  # WRONG_SUBNET_MASK_R1",
    },
    {
        "code": "VLAN_MISMATCH",
        "topic": "vlan_like",
        "device": "r1",
        "description": "VLAN-like interface mismatch on r1 eth1.",
        "severity": "medium",
        "config_line": "interface eth1 vlan 999  # VLAN_MISMATCH",
    },
    {
        "code": "ACL_BLOCK_ICMP_R1",
        "topic": "acl_like",
        "device": "r1",
        "description": "Policy-like rule blocks expected ICMP troubleshooting traffic on r1.",
        "severity": "high",
        "config_line": "access-list AUTONETLAB-DEMO deny icmp any any  # ACL_BLOCK_ICMP_R1",
    },
    {
        "code": "MISSING_ROUTE",
        "topic": "static_routing",
        "device": "r2",
        "description": "Required static route is missing on r2.",
        "severity": "medium",
        "config_line": "no ip route 10.10.30.0/24 via 10.10.20.1  # MISSING_ROUTE",
    },
    {
        "code": "WRONG_GATEWAY",
        "topic": "default_gateway",
        "device": "r2",
        "description": "Wrong default gateway configured on r2.",
        "severity": "medium",
        "config_line": "ip route 0.0.0.0/0 via 10.10.10.254  # WRONG_GATEWAY",
    },
    {
        "code": "INTERFACE_DOWN_R2",
        "topic": "interface_status",
        "device": "r2",
        "description": "Interface eth1 is administratively down on r2.",
        "severity": "medium",
        "config_line": "interface eth1 shutdown  # INTERFACE_DOWN_R2",
    },
    {
        "code": "CONNECTIVITY_FAILURE_R2_R3",
        "topic": "connectivity",
        "device": "r2",
        "description": "Connectivity between r2 and r3 is broken by an incorrect link-side setting.",
        "severity": "high",
        "config_line": "interface eth2 connectivity-check failed  # CONNECTIVITY_FAILURE_R2_R3",
    },
    {
        "code": "WRONG_SUBNET_MASK",
        "topic": "subnetting",
        "device": "r3",
        "description": "Wrong subnet mask configured on r3 eth1.",
        "severity": "low",
        "config_line": "interface eth1 ip address 10.10.23.2/16  # WRONG_SUBNET_MASK",
    },
    {
        "code": "MISSING_ROUTE_R3",
        "topic": "static_routing",
        "device": "r3",
        "description": "Required route is missing on r3.",
        "severity": "medium",
        "config_line": "no ip route 10.10.12.0/24 via 10.10.23.1  # MISSING_ROUTE_R3",
    },
    {
        "code": "VLAN_MISMATCH_R3",
        "topic": "vlan_like",
        "device": "r3",
        "description": "VLAN-like mismatch exists on r3 eth2.",
        "severity": "medium",
        "config_line": "interface eth2 vlan 300  # VLAN_MISMATCH_R3",
    },
    {
        "code": "ACL_BLOCK_ICMP_R3",
        "topic": "acl_like",
        "device": "r3",
        "description": "Policy-like rule blocks expected ICMP troubleshooting traffic on r3.",
        "severity": "high",
        "config_line": "access-list AUTONETLAB-DEMO deny icmp any any  # ACL_BLOCK_ICMP_R3",
    },
    {
        "code": "INTERFACE_DOWN_R4",
        "topic": "interface_status",
        "device": "r4",
        "description": "Interface eth1 is administratively down on r4.",
        "severity": "high",
        "config_line": "interface eth1 shutdown  # INTERFACE_DOWN_R4",
    },
    {
        "code": "WRONG_GATEWAY_R4",
        "topic": "default_gateway",
        "device": "r4",
        "description": "Wrong default gateway configured on r4.",
        "severity": "high",
        "config_line": "ip route 0.0.0.0/0 via 10.10.34.254  # WRONG_GATEWAY_R4",
    },
    {
        "code": "CONNECTIVITY_FAILURE_R1_R4",
        "topic": "connectivity",
        "device": "r4",
        "description": "Backup connectivity between r1 and r4 is broken by an incorrect link-side setting.",
        "severity": "high",
        "config_line": "interface eth2 connectivity-check failed  # CONNECTIVITY_FAILURE_R1_R4",
    },
]


ERROR_COUNT_BY_DIFFICULTY = {
    Difficulty.easy: 2,
    Difficulty.medium: 3,
    Difficulty.hard: 5,
}


BASE_CONFIG_BY_DEVICE = {
    "r1": [
        "# AutoNetLab generated config for r1",
        "hostname r1",
        "interface eth1 ip address 10.10.12.1/24",
        "interface eth2 ip address 10.10.14.1/24",
    ],
    "r2": [
        "# AutoNetLab generated config for r2",
        "hostname r2",
        "interface eth1 ip address 10.10.12.2/24",
        "interface eth2 ip address 10.10.23.1/24",
        "ip route 0.0.0.0/0 via 10.10.12.1",
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
        "ip route 10.10.12.0/24 via 10.10.14.1",
    ],
}


def generate_errors(
    difficulty: Difficulty,
    seed: str,
    topology_devices: list[str] | None = None,
) -> list[ErrorItem]:
    """
    Generates deterministic/reproducible error metadata.

    Tekrar üretilebilirlik:
    - same seed/tohum değer
    - same difficulty/zorluk
    - same topology device list/topoloji cihaz listesi
    -> same injected error list.
    """

    selected_errors = _select_errors(
        difficulty=difficulty,
        seed=seed,
        topology_devices=topology_devices,
    )

    return [
        ErrorItem(
            code=error["code"],
            topic=error["topic"],
            device=error["device"],
            description=error["description"],
            severity=error["severity"],
        )
        for error in selected_errors
    ]


def apply_error_injection(
    difficulty: Difficulty,
    seed: str,
    session_dir: Path,
    topology_devices: list[str] | None = None,
) -> list[ErrorItem]:
    """
    Applies Error Injection v3 / Hata Enjeksiyonu v3.

    Sprint 8 improvements:
    - Uses canonical error taxonomy / standart hata sınıflandırması.
    - Adds richer hard scenarios / daha gerçekçi zor senaryolar.
    - Keeps deterministic selection / tekrar üretilebilir seçim.
    - Keeps existing config-marker validation compatibility.
    """

    selected_errors = _select_errors(
        difficulty=difficulty,
        seed=seed,
        topology_devices=topology_devices,
    )

    error_items = [
        ErrorItem(
            code=error["code"],
            topic=error["topic"],
            device=error["device"],
            description=error["description"],
            severity=error["severity"],
        )
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


def _select_errors(
    difficulty: Difficulty,
    seed: str,
    topology_devices: list[str] | None = None,
) -> list[dict]:
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

    return randomizer.sample(available_errors, count)


def _available_errors_for_topology(topology_devices: list[str] | None = None) -> list[dict]:
    allowed_devices = set(topology_devices or [])

    if not allowed_devices:
        return list(ERROR_POOL)

    return [
        error
        for error in ERROR_POOL
        if error["device"] in allowed_devices
    ]


def _select_diverse_hard_errors(
    available_errors: list[dict],
    count: int,
    randomizer: random.Random,
) -> list[dict]:
    """
    Selects hard errors with topic and device diversity.

    Sprint 19 adds a stronger hard-scenario guarantee:
    - keep deterministic selection,
    - avoid five checks from one topic,
    - when the hard topology has at least three devices, cover at least
      three different devices in the selected error set.
    """

    selected_errors: list[dict] = []
    selected_codes: set[str] = set()

    available_devices = sorted(
        {
            str(error["device"])
            for error in available_errors
            if error.get("device")
        }
    )
    randomizer.shuffle(available_devices)

    minimum_device_count = min(3, count, len(available_devices))

    for device in available_devices[:minimum_device_count]:
        device_candidates = [
            error
            for error in available_errors
            if error.get("device") == device
        ]

        if not device_candidates:
            continue

        selected_error = randomizer.choice(device_candidates)
        selected_errors.append(selected_error)
        selected_codes.add(selected_error["code"])

    errors_by_topic: dict[str, list[dict]] = defaultdict(list)

    for error in available_errors:
        if error["code"] in selected_codes:
            continue

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

        selected_error = randomizer.choice(errors_by_topic[topic])
        selected_errors.append(selected_error)
        selected_codes.add(selected_error["code"])
        selected_topics.add(topic)

    if len(selected_errors) < count:
        remaining_errors = [
            error
            for error in available_errors
            if error["code"] not in selected_codes
        ]

        randomizer.shuffle(remaining_errors)

        for error in remaining_errors:
            if len(selected_errors) >= count:
                break

            selected_errors.append(error)
            selected_codes.add(error["code"])

    return selected_errors


def _write_device_configs(
    configs_dir: Path,
    selected_errors: list[dict],
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
        config_by_device[device].append("# Injected error / enjekte edilen hata")
        config_by_device[device].append(f"# {error['code']}: {error['description']}")
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
        "error_taxonomy": [
            "ip_addressing",
            "subnetting",
            "interface_status",
            "default_gateway",
            "static_routing",
            "vlan_like",
            "acl_like",
            "connectivity",
        ],
        "injected_errors": [
            error.model_dump()
            for error in error_items
        ],
    }

    metadata_path.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )