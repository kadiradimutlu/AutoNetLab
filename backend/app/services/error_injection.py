import random

from app.schemas.enums import Difficulty
from app.schemas.lab import ErrorItem


ERROR_POOL = [
    {
        "code": "IP_ADDRESS_MISMATCH",
        "topic": "IP Addressing",
        "device": "r1",
        "description": "Incorrect IP address configured on r1 eth1.",
        "severity": "low",
    },
    {
        "code": "WRONG_SUBNET_MASK",
        "topic": "IP Addressing",
        "device": "r2",
        "description": "Wrong subnet mask configured on r2 eth1.",
        "severity": "low",
    },
    {
        "code": "VLAN_MISMATCH",
        "topic": "VLAN",
        "device": "r1",
        "description": "VLAN ID mismatch on r1 interface.",
        "severity": "medium",
    },
    {
        "code": "MISSING_ROUTE",
        "topic": "Routing",
        "device": "r2",
        "description": "Static route is missing on r2.",
        "severity": "medium",
    },
    {
        "code": "ACL_DENY_ANY",
        "topic": "ACL",
        "device": "r1",
        "description": "ACL rule blocks all traffic unexpectedly.",
        "severity": "high",
    },
]


ERROR_COUNT_BY_DIFFICULTY = {
    Difficulty.easy: 2,
    Difficulty.medium: 3,
    Difficulty.hard: 5,
}


def generate_errors(difficulty: Difficulty, seed: str) -> list[ErrorItem]:
    """
    Generates deterministic random errors for the same session id.

    Deterministic means:
    - same session_id -> same error list
    - useful for reproducibility/session continuity
    """

    count = ERROR_COUNT_BY_DIFFICULTY[difficulty]
    randomizer = random.Random(seed)
    selected_errors = randomizer.sample(ERROR_POOL, count)

    return [ErrorItem(**error) for error in selected_errors]