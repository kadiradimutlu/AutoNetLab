from dataclasses import dataclass


@dataclass(frozen=True)
class LiveValidationRule:
    """
    Defines how an injected error is validated against live container state.

    Random lab generation can choose different errors, but every selectable
    error code must have a deterministic validation rule here.
    """

    command: str
    expected_outputs: tuple[str, ...]
    description: str


def _rule(
    command: str,
    expected_output: str | tuple[str, ...],
    description: str,
) -> LiveValidationRule:
    expected_outputs = (
        (expected_output,)
        if isinstance(expected_output, str)
        else tuple(expected_output)
    )

    return LiveValidationRule(
        command=command,
        expected_outputs=expected_outputs,
        description=description,
    )


ERROR_VALIDATION_RULES: dict[str, LiveValidationRule] = {
    "IP_ADDRESS_MISMATCH": _rule(
        command="ip addr show eth1",
        expected_output="inet 10.10.12.1/24",
        description="r1 eth1 should use the correct r1-r2 link IP address.",
    ),
    "WRONG_SUBNET_MASK_R1": _rule(
        command="ip addr show eth1",
        expected_output="inet 10.10.12.1/24",
        description="r1 eth1 should use the correct /24 mask.",
    ),
    "VLAN_MISMATCH": _rule(
        command="ip addr show eth2",
        expected_output="inet 10.10.14.1/24",
        description="r1 eth2 should be restored to the expected r1-r4 link-side state.",
    ),
    "ACL_BLOCK_ICMP_R1": _rule(
        command="ping -c 1 -W 1 10.10.12.2",
        expected_output="1 packets received",
        description="r1 should be able to reach r2 over ICMP.",
    ),
    "MISSING_ROUTE": _rule(
        command="ip route",
        expected_output="10.10.34.0/24 via 10.10.23.2",
        description="r2 should have the route toward the r3-r4 network.",
    ),
    "WRONG_GATEWAY": _rule(
        command="ip route",
        expected_output="default via 10.10.12.1",
        description="r2 should use r1 as the default gateway.",
    ),
    "INTERFACE_DOWN_R2": _rule(
        command="ip link show eth1",
        expected_output="state UP",
        description="r2 eth1 should be operational.",
    ),
    "CONNECTIVITY_FAILURE_R2_R3": _rule(
        command="ping -c 1 -W 1 10.10.23.2",
        expected_output="1 packets received",
        description="r2 should be able to reach r3 over the r2-r3 link.",
    ),
    "WRONG_SUBNET_MASK": _rule(
        command="ip addr show eth1",
        expected_output="inet 10.10.23.2/24",
        description="r3 eth1 should use the correct /24 mask.",
    ),
    "MISSING_ROUTE_R3": _rule(
        command="ip route",
        expected_output="10.10.12.0/24 via 10.10.23.1",
        description="r3 should have the route toward the r1-r2 network.",
    ),
    "VLAN_MISMATCH_R3": _rule(
        command="ip addr show eth2",
        expected_output="inet 10.10.34.1/24",
        description="r3 eth2 should be restored to the expected r3-r4 link-side state.",
    ),
    "ACL_BLOCK_ICMP_R3": _rule(
        command="ping -c 1 -W 1 10.10.23.1",
        expected_output="1 packets received",
        description="r3 should be able to reach r2 over ICMP.",
    ),
    "INTERFACE_DOWN_R4": _rule(
        command="ip link show eth1",
        expected_output="state UP",
        description="r4 eth1 should be operational.",
    ),
    "WRONG_GATEWAY_R4": _rule(
        command="ip route",
        expected_output="default via 10.10.34.1",
        description="r4 should use r3 as the default gateway.",
    ),
    "CONNECTIVITY_FAILURE_R1_R4": _rule(
        command="ping -c 1 -W 1 10.10.14.1",
        expected_output="1 packets received",
        description="r4 should be able to reach r1 over the backup r1-r4 link.",
    ),
}


def get_live_validation_rule(code: str) -> LiveValidationRule | None:
    return ERROR_VALIDATION_RULES.get(code)


def supported_live_validation_codes() -> set[str]:
    return set(ERROR_VALIDATION_RULES)
