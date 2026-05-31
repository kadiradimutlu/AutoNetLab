import re
from app.schemas.enums import Difficulty
from app.services.scenario_catalog import (
    BRANCH_STATIC_ROUTING_SCENARIO_ID,
    CAMPUS_CORE_ROUTING_SCENARIO_ID,
    SR_EDGE_LINK_SCENARIO_ID,
)
from app.services.srlinux_runtime_setup import (
    BRANCH_CLIENT2_INJECTED_GATEWAY,
    BRANCH_CLIENT2_EXPECTED_GATEWAY,
    BRANCH_WRONG_CLIENT2_GATEWAY_CODE,
    CAMPUS_WRONG_CLIENT2_GATEWAY_CODE,
    SRLINUX_WRONG_CLIENT_GATEWAY_CODE,
    _runtime_fault_catalog_for_scenario,
    build_srlinux_runtime_faults,
)


def _variant_ids(faults):
    return [fault["variant_id"] for fault in faults]


def _conflict_keys(faults):
    return [fault["conflict_key"] for fault in faults]


def test_checkpoint3_catalog_contains_30_plus_srlinux_compatible_variants():
    edge_catalog = _runtime_fault_catalog_for_scenario(
        scenario_id=SR_EDGE_LINK_SCENARIO_ID,
        seed="catalog-edge",
    )
    branch_catalog = _runtime_fault_catalog_for_scenario(
        scenario_id=BRANCH_STATIC_ROUTING_SCENARIO_ID,
        seed="catalog-branch",
    )
    campus_catalog = _runtime_fault_catalog_for_scenario(
        scenario_id=CAMPUS_CORE_ROUTING_SCENARIO_ID,
        seed="catalog-campus",
    )

    all_faults = [*edge_catalog, *branch_catalog, *campus_catalog]

    assert len(edge_catalog) >= 8
    assert len(branch_catalog) >= 12
    assert len(campus_catalog) >= 16
    assert len(all_faults) >= 30

    variant_ids = _variant_ids(all_faults)
    assert len(variant_ids) == len(set(variant_ids))

    for fault in all_faults:
        assert fault["scenario_id"] in {
            SR_EDGE_LINK_SCENARIO_ID,
            BRANCH_STATIC_ROUTING_SCENARIO_ID,
            CAMPUS_CORE_ROUTING_SCENARIO_ID,
        }
        assert fault["variant_id"]
        assert fault["code"]
        assert fault["topic"] in {
            "default_gateway",
            "ip_addressing",
            "interface_state",
            "network_instance",
            "static_routing",
        }
        assert fault["device"]
        assert fault["conflict_key"]
        assert fault["expected_outputs"]
        assert fault["injection_commands"]
        assert all(str(command).strip() for command in fault["injection_commands"])


def test_checkpoint3_difficulty_controls_selected_fault_count_for_each_scenario():
    for scenario_id in [
        SR_EDGE_LINK_SCENARIO_ID,
        BRANCH_STATIC_ROUTING_SCENARIO_ID,
        CAMPUS_CORE_ROUTING_SCENARIO_ID,
    ]:
        easy_faults = build_srlinux_runtime_faults(
            difficulty=Difficulty.easy,
            seed=f"{scenario_id}-easy",
            scenario_id=scenario_id,
        )
        medium_faults = build_srlinux_runtime_faults(
            difficulty=Difficulty.medium,
            seed=f"{scenario_id}-medium",
            scenario_id=scenario_id,
        )
        hard_faults = build_srlinux_runtime_faults(
            difficulty=Difficulty.hard,
            seed=f"{scenario_id}-hard",
            scenario_id=scenario_id,
        )

        assert len(easy_faults) == 1
        assert len(medium_faults) == 2
        assert len(hard_faults) == 3


def test_checkpoint3_selection_is_deterministic_for_same_seed_and_varies_across_new_seeds():
    scenario_id = CAMPUS_CORE_ROUTING_SCENARIO_ID

    first = build_srlinux_runtime_faults(
        difficulty=Difficulty.hard,
        seed="lab-deterministic-001",
        scenario_id=scenario_id,
    )
    second = build_srlinux_runtime_faults(
        difficulty=Difficulty.hard,
        seed="lab-deterministic-001",
        scenario_id=scenario_id,
    )

    assert _variant_ids(first) == _variant_ids(second)

    seen = {
        tuple(
            _variant_ids(
                build_srlinux_runtime_faults(
                    difficulty=Difficulty.hard,
                    seed=f"lab-randomized-{index}",
                    scenario_id=scenario_id,
                )
            )
        )
        for index in range(10)
    }

    assert len(seen) > 1


def test_checkpoint3_selected_faults_do_not_conflict_in_hard_labs():
    for scenario_id in [
        SR_EDGE_LINK_SCENARIO_ID,
        BRANCH_STATIC_ROUTING_SCENARIO_ID,
        CAMPUS_CORE_ROUTING_SCENARIO_ID,
    ]:
        for index in range(15):
            faults = build_srlinux_runtime_faults(
                difficulty=Difficulty.hard,
                seed=f"{scenario_id}-hard-conflict-{index}",
                scenario_id=scenario_id,
            )
            conflict_keys = _conflict_keys(faults)

            assert len(faults) == 3
            assert len(conflict_keys) == len(set(conflict_keys))


def test_checkpoint3_existing_primary_faults_remain_first_for_backward_compatibility():
    edge_faults = build_srlinux_runtime_faults(
        difficulty=Difficulty.easy,
        seed="lab-edge",
        scenario_id=SR_EDGE_LINK_SCENARIO_ID,
    )
    branch_faults = build_srlinux_runtime_faults(
        difficulty=Difficulty.easy,
        seed="lab-branch",
        scenario_id=BRANCH_STATIC_ROUTING_SCENARIO_ID,
    )
    campus_faults = build_srlinux_runtime_faults(
        difficulty=Difficulty.easy,
        seed="lab-campus",
        scenario_id=CAMPUS_CORE_ROUTING_SCENARIO_ID,
    )

    assert edge_faults[0]["code"] == SRLINUX_WRONG_CLIENT_GATEWAY_CODE
    assert branch_faults[0]["code"] == BRANCH_WRONG_CLIENT2_GATEWAY_CODE
    assert branch_faults[0]["expected_outputs"] == [
        f"default via {BRANCH_CLIENT2_EXPECTED_GATEWAY}"
    ]
    assert branch_faults[0]["injection_commands"] == [
        f"ip route replace default via {BRANCH_CLIENT2_INJECTED_GATEWAY} dev eth1"
    ]
    assert campus_faults[0]["code"] == CAMPUS_WRONG_CLIENT2_GATEWAY_CODE


def test_checkpoint3_safe_wrong_values_do_not_equal_expected_outputs_for_randomized_faults():
    for scenario_id in [
        SR_EDGE_LINK_SCENARIO_ID,
        BRANCH_STATIC_ROUTING_SCENARIO_ID,
        CAMPUS_CORE_ROUTING_SCENARIO_ID,
    ]:
        faults = _runtime_fault_catalog_for_scenario(
            scenario_id=scenario_id,
            seed=f"{scenario_id}-safe-values",
        )

        for fault in faults:
            command_blob = "\n".join(fault["injection_commands"])

            for expected_output in fault["expected_outputs"]:
                if "default via" in expected_output:
                    expected_gateway = expected_output.removeprefix("default via ").strip()
                    assert f"replace default via {expected_gateway}" not in command_blob
                    assert f"add default via {expected_gateway}" not in command_blob

                if "/" in expected_output and "address" in command_blob:
                    # SR Linux wrong-IP faults may delete the expected address
                    # before setting a safe wrong address. The unsafe case is
                    # setting/adding the expected address as the injected value.
                    assert f"ip addr add {expected_output}" not in command_blob
                    assert re.search(
                        rf"set interface .* address {re.escape(expected_output)}(?:'|$)",
                        command_blob,
                    ) is None
