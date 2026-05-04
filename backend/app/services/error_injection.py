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
        "config_line": "interface eth1 ip address 10.10.10.99/24  # injected wrong IP",
    },
    {
        "code": "VLAN_MISMATCH",
        "topic": "VLAN",
        "device": "r1",
        "description": "VLAN ID mismatch on r1 interface eth1.",
        "severity": "medium",
        "config_line": "interface eth1 vlan 999  # injected wrong VLAN",
    },
    {
        "code": "MISSING_ROUTE",
        "topic": "Routing",
        "device": "r2",
        "description": "Required static route is missing on r2.",
        "severity": "medium",
        "config_line": "no ip route 10.10.30.0/24 via 10.10.20.1  # injected missing route",
    },
    {
        "code": "WRONG_GATEWAY",
        "topic": "Default Gateway",
        "device": "r2",
        "description": "Wrong default gateway configured on r2.",
        "severity": "medium",
        "config_line": "ip route 0.0.0.0/0 via 10.10.10.254  # injected wrong gateway",
    },
    {
        "code": "WRONG_SUBNET_MASK",
        "topic": "IP Addressing",
        "device": "r3",
        "description": "Wrong subnet mask configured on r3 eth1.",
        "severity": "low",
        "config_line": "interface eth1 ip address 10.10.30.2/16  # injected wrong subnet mask",
    },
    {
        "code": "ACL_DENY_ANY",
        "topic": "ACL",
        "device": "r4",
        "description": "ACL rule blocks all traffic unexpectedly.",
        "severity": "high",
        "config_line": "access-list 100 deny ip any any  # injected blocking ACL",
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
    ],
    "r4": [
        "# AutoNetLab generated config for r4",
        "hostname r4",
        "interface eth1 ip address 10.10.34.2/24",
        "interface eth2 ip address 10.10.14.2/24",
    ],
}


def generate_errors(difficulty: Difficulty, seed: str) -> list[ErrorItem]:
    """
    Generates deterministic random error metadata for the same session id.

    Deterministic / tekrarlanabilir:
    - same session_id -> same error list
    - useful for session continuity and validation/doğrulama
    """

    selected_errors = _select_errors(difficulty=difficulty, seed=seed)

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
) -> list[ErrorItem]:
    """
    Applies Error Injection v1 / Hata Enjeksiyonu v1.

    MVP yaklaşımı:
    - Real router configuration is not required yet.
    - We create session-specific metadata and simple device config files.
    - Validation service can later read these files.

    Output:
    - containerlab/generated/<session_id>/errors/injected_errors.json
    - containerlab/generated/<session_id>/configs/<device>.conf
    """

    selected_errors = _select_errors(difficulty=difficulty, seed=seed)
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
    )

    _write_error_metadata(
        errors_dir=errors_dir,
        error_items=error_items,
    )

    return error_items


def _select_errors(difficulty: Difficulty, seed: str) -> list[dict]:
    count = ERROR_COUNT_BY_DIFFICULTY[difficulty]
    randomizer = random.Random(seed)

    available_errors = list(ERROR_POOL)

    if count > len(available_errors):
        count = len(available_errors)

    return randomizer.sample(available_errors, count)


def _write_device_configs(
    configs_dir: Path,
    selected_errors: list[dict],
) -> None:
    config_by_device = {
        device: list(lines)
        for device, lines in BASE_CONFIG_BY_DEVICE.items()
    }

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
) -> None:
    metadata_path = errors_dir / "injected_errors.json"

    payload = {
        "injected_errors": [
            error.model_dump()
            for error in error_items
        ]
    }

    metadata_path.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )
