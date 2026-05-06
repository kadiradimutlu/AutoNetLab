import json
import random
from pathlib import Path

from app.schemas.enums import Difficulty
from app.schemas.lab import ErrorItem


ERROR_POOL = [
    {
        "code": "IP_ADDRESS_MISMATCH",
        "topic": "IP Addressing",
        "device": "r1",
        "description": "Incorrect IP address configured on r1 eth1.",
        "severity": "low",
        "config_line": "interface eth1 ip address 10.10.10.99/24  # IP_ADDRESS_MISMATCH",
    },
    {
        "code": "VLAN_MISMATCH",
        "topic": "VLAN",
        "device": "r1",
        "description": "VLAN ID mismatch on r1 interface eth1.",
        "severity": "medium",
        "config_line": "interface eth1 vlan 999  # VLAN_MISMATCH",
    },
    {
        "code": "MISSING_ROUTE",
        "topic": "Routing",
        "device": "r2",
        "description": "Required static route is missing on r2.",
        "severity": "medium",
        "config_line": "no ip route 10.10.30.0/24 via 10.10.20.1  # MISSING_ROUTE",
    },
    {
        "code": "WRONG_GATEWAY",
        "topic": "Default Gateway",
        "device": "r2",
        "description": "Wrong default gateway configured on r2.",
        "severity": "medium",
        "config_line": "ip route 0.0.0.0/0 via 10.10.10.254  # WRONG_GATEWAY",
    },
    {
        "code": "INTERFACE_DOWN_R2",
        "topic": "Interface Status",
        "device": "r2",
        "description": "Interface eth1 is administratively down on r2.",
        "severity": "medium",
        "config_line": "interface eth1 shutdown  # INTERFACE_DOWN_R2",
    },
    {
        "code": "WRONG_SUBNET_MASK",
        "topic": "IP Addressing",
        "device": "r3",
        "description": "Wrong subnet mask configured on r3 eth1.",
        "severity": "low",
        "config_line": "interface eth1 ip address 10.10.23.2/16  # WRONG_SUBNET_MASK",
    },
    {
        "code": "MISSING_ROUTE_R3",
        "topic": "Routing",
        "device": "r3",
        "description": "Required route is missing on r3.",
        "severity": "medium",
        "config_line": "no ip route 10.10.12.0/24 via 10.10.23.1  # MISSING_ROUTE_R3",
    },
    {
        "code": "VLAN_MISMATCH_R3",
        "topic": "VLAN",
        "device": "r3",
        "description": "VLAN mismatch exists on r3 eth2.",
        "severity": "medium",
        "config_line": "interface eth2 vlan 300  # VLAN_MISMATCH_R3",
    },
    {
        "code": "INTERFACE_DOWN_R4",
        "topic": "Interface Status",
        "device": "r4",
        "description": "Interface eth1 is administratively down on r4.",
        "severity": "high",
        "config_line": "interface eth1 shutdown  # INTERFACE_DOWN_R4",
    },
    {
        "code": "WRONG_GATEWAY_R4",
        "topic": "Default Gateway",
        "device": "r4",
        "description": "Wrong default gateway configured on r4.",
        "severity": "high",
        "config_line": "ip route 0.0.0.0/0 via 10.10.34.254  # WRONG_GATEWAY_R4",
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
    ],
    "r2": [
        "# AutoNetLab generated config for r2",
        "hostname r2",
        "interface eth1 ip address 10.10.12.2/24",
        "interface eth2 ip address 10.10.23.1/24",
        "ip route 0.0.0.0/0 via 10.10.12.1",
    ],
    "r3": [
        "# AutoNetLab generated config for r3",
        "hostname r3",
        "interface eth1 ip address 10.10.23.2/24",
        "interface eth2 ip address 10.10.34.1/24",
        "ip route 10.10.12.0/24 via 10.10.23.1",
    ],
    "r4": [
        "# AutoNetLab generated config for r4",
        "hostname r4",
        "interface eth1 ip address 10.10.34.2/24",
        "interface eth2 ip address 10.10.14.2/24",
        "ip route 0.0.0.0/0 via 10.10.34.1",
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
    Applies Error Injection v2 / Hata Enjeksiyonu v2.

    Sprint 3 improvements:
    - Error selection is deterministic/reproducible by seed.
    - Errors are selected only from devices that exist in the generated topology.
    - Session-specific metadata and config files are written under generated session folder.

    Output:
    - containerlab/generated/<session_id>/errors/injected_errors.json
    - containerlab/generated/<session_id>/configs/<device>.conf
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

    allowed_devices = set(topology_devices or [])

    if allowed_devices:
        available_errors = [
            error
            for error in ERROR_POOL
            if error["device"] in allowed_devices
        ]
    else:
        available_errors = list(ERROR_POOL)

    if not available_errors:
        return []

    if count > len(available_errors):
        count = len(available_errors)

    return randomizer.sample(available_errors, count)


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
        "injected_errors": [
            error.model_dump()
            for error in error_items
        ],
    }

    metadata_path.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )