import shutil

from app.schemas.enums import Difficulty
from app.services.scenario_catalog import (
    BRANCH_STATIC_ROUTING_SCENARIO_ID,
    CAMPUS_CORE_ROUTING_SCENARIO_ID,
    CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID,
    DEFAULT_SCENARIO_ID,
    DIFFICULTY_FAULT_COUNTS,
    SR_BASIC_LINK_SCENARIO_ID,
    SR_EDGE_LINK_SCENARIO_ID,
    get_scenario,
    is_srlinux_scenario,
    list_scenarios,
    resolve_scenario_id,
)
from app.services.topology_generator import GENERATED_DIR, generate_session_topology


REQUIRED_SCENARIO_KEYS = {
    "id",
    "title",
    "summary",
    "objective",
    "story",
    "topology_template",
    "topology_metadata",
    "addressing_table",
    "interface_requirements",
    "routing_requirements",
    "expected_connectivity",
    "expected_network_state",
    "student_tasks",
    "supported_difficulties",
    "difficulty_fault_counts",
}


def _cleanup(session_id: str) -> None:
    generated_dir = GENERATED_DIR / session_id
    if generated_dir.exists():
        shutil.rmtree(generated_dir)


def test_product_scenario_catalog_exposes_three_canonical_scenarios_only():
    scenarios = list_scenarios()
    scenario_ids = [scenario["id"] for scenario in scenarios]

    assert scenario_ids == [
        SR_EDGE_LINK_SCENARIO_ID,
        BRANCH_STATIC_ROUTING_SCENARIO_ID,
        CAMPUS_CORE_ROUTING_SCENARIO_ID,
    ]
    assert SR_BASIC_LINK_SCENARIO_ID not in scenario_ids
    assert CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID not in scenario_ids
    assert DEFAULT_SCENARIO_ID == SR_EDGE_LINK_SCENARIO_ID


def test_each_product_scenario_has_expected_network_state_contract():
    for scenario in list_scenarios():
        assert REQUIRED_SCENARIO_KEYS.issubset(scenario)
        assert scenario["router_os"] == "Nokia SR Linux"
        assert scenario["runtime_profile"] == "runtime_fault_injection"
        assert scenario["supported_difficulties"] == ["easy", "medium", "hard"]
        assert scenario["difficulty_fault_counts"] == DIFFICULTY_FAULT_COUNTS
        assert scenario["addressing_table"]
        assert scenario["interface_requirements"]
        assert scenario["routing_requirements"]
        assert scenario["expected_connectivity"]
        assert scenario["student_tasks"]

        expected_state = scenario["expected_network_state"]
        assert expected_state["addressing_table"] == scenario["addressing_table"]
        assert expected_state["interface_requirements"] == scenario["interface_requirements"]
        assert expected_state["routing_requirements"] == scenario["routing_requirements"]
        assert expected_state["expected_connectivity"] == scenario["expected_connectivity"]


def test_legacy_scenario_ids_resolve_to_canonical_contracts():
    assert resolve_scenario_id(SR_BASIC_LINK_SCENARIO_ID) == SR_EDGE_LINK_SCENARIO_ID
    assert resolve_scenario_id(CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID) == CAMPUS_CORE_ROUTING_SCENARIO_ID

    edge = get_scenario(SR_BASIC_LINK_SCENARIO_ID)
    campus = get_scenario(CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID)

    assert edge["id"] == SR_EDGE_LINK_SCENARIO_ID
    assert edge["legacy_alias"] == SR_BASIC_LINK_SCENARIO_ID
    assert campus["id"] == CAMPUS_CORE_ROUTING_SCENARIO_ID
    assert campus["legacy_alias"] == CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID

    assert is_srlinux_scenario(SR_BASIC_LINK_SCENARIO_ID) is True
    assert is_srlinux_scenario(CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID) is True


def test_product_scenario_topology_generation_shapes():
    cases = [
        (SR_EDGE_LINK_SCENARIO_ID, 2, 1),
        (BRANCH_STATIC_ROUTING_SCENARIO_ID, 4, 3),
        (CAMPUS_CORE_ROUTING_SCENARIO_ID, 6, 6),
    ]

    for scenario_id, expected_nodes, expected_links in cases:
        session_id = f"pytest-40a-{scenario_id}"
        try:
            result = generate_session_topology(
                session_id=session_id,
                difficulty=Difficulty.hard,
                scenario_id=scenario_id,
            )

            topology = result["topology"]

            assert result["topology_template"] == scenario_id
            assert len(topology.nodes) == expected_nodes
            assert len(topology.links) == expected_links
            assert (GENERATED_DIR / session_id / "lab.clab.yml").exists()
        finally:
            _cleanup(session_id)
