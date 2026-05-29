import shutil
from pathlib import Path

import yaml
from fastapi import HTTPException

from app.schemas.enums import Difficulty
from app.services.scenario_catalog import (
    SR_BASIC_LINK_SCENARIO_ID,
    get_scenario,
    is_srlinux_scenario,
    list_scenarios,
)
from app.services.topology_generator import GENERATED_DIR, generate_session_topology


def test_scenario_catalog_exposes_srlinux_basic_link():
    scenarios = list_scenarios()

    scenario = next(
        item
        for item in scenarios
        if item["id"] == SR_BASIC_LINK_SCENARIO_ID
    )

    assert scenario["router_os"] == "Nokia SR Linux"
    assert scenario["topology_template"] == "srl-basic-link"
    assert scenario["addressing_table"]
    assert scenario["routing_requirements"]
    assert scenario["expected_connectivity"]
    assert is_srlinux_scenario(SR_BASIC_LINK_SCENARIO_ID) is True


def test_unknown_scenario_rejected():
    try:
        get_scenario("does-not-exist")
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "Unsupported scenario_id" in str(exc.detail)
    else:
        raise AssertionError("Unknown scenario_id should raise HTTPException.")


def test_generate_srlinux_basic_link_topology_file():
    session_id = "lab-sprint30-srl-test"
    generated_dir = GENERATED_DIR / session_id

    if generated_dir.exists():
        shutil.rmtree(generated_dir)

    try:
        result = generate_session_topology(
            session_id=session_id,
            difficulty=Difficulty.easy,
            topology_template="basic-two-router",
            scenario_id=SR_BASIC_LINK_SCENARIO_ID,
        )

        topology = result["topology"]
        topology_file = Path(result["topology_file"])

        assert result["topology_template"] == "srl-basic-link"
        assert topology_file.exists()

        node_by_id = {
            node.id: node
            for node in topology.nodes
        }

        assert node_by_id["srl1"].kind == "nokia_srlinux"
        assert node_by_id["srl1"].image == "ghcr.io/nokia/srlinux:26.3.2"
        assert node_by_id["client1"].kind == "linux"
        assert node_by_id["client1"].image == "ghcr.io/srl-labs/network-multitool:latest"

        payload = yaml.safe_load(topology_file.read_text(encoding="utf-8"))

        assert payload["topology"]["nodes"]["srl1"]["kind"] == "nokia_srlinux"
        assert payload["topology"]["nodes"]["srl1"]["type"] == "ixr-d2l"
        assert payload["topology"]["nodes"]["client1"]["kind"] == "linux"
        assert payload["topology"]["links"][0]["endpoints"] == [
            "srl1:e1-1",
            "client1:eth1",
        ]
    finally:
        if generated_dir.exists():
            shutil.rmtree(generated_dir)


def test_meta_scenarios_api_exposes_srlinux_catalog():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)

    response = client.get("/api/v1/meta/scenarios")

    assert response.status_code == 200

    payload = response.json()
    assert payload["success"] is True
    assert payload["message"] == "Scenario catalog retrieved successfully."

    scenario_by_id = {
        scenario["id"]: scenario
        for scenario in payload["scenarios"]
    }

    scenario = scenario_by_id[SR_BASIC_LINK_SCENARIO_ID]

    assert scenario["title"] == "SR Linux Basic Link Troubleshooting"
    assert scenario["router_os"] == "Nokia SR Linux"
    assert scenario["addressing_table"]
    assert scenario["routing_requirements"]
    assert scenario["expected_connectivity"]


def test_create_lab_with_srlinux_scenario_returns_student_safe_contract():
    from uuid import uuid4

    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    student_id = f"pytest-sprint30-{uuid4().hex[:8]}"

    response = client.post(
        "/api/v1/labs",
        json={
            "student_id": student_id,
            "difficulty": "easy",
            "scenario_id": SR_BASIC_LINK_SCENARIO_ID,
        },
    )

    assert response.status_code == 201

    payload = response.json()
    session_id = payload["session_id"]
    generated_dir = GENERATED_DIR / session_id

    try:
        assert payload["scenario"]["id"] == SR_BASIC_LINK_SCENARIO_ID
        assert payload["scenario"]["addressing_table"]
        assert payload["scenario"]["routing_requirements"]
        assert payload["scenario"]["expected_connectivity"]

        assert "injected_errors" not in payload
        assert "runtime_cleanup_history" not in payload

        node_by_id = {
            node["id"]: node
            for node in payload["topology"]["nodes"]
        }

        assert node_by_id["srl1"]["kind"] == "nokia_srlinux"
        assert node_by_id["srl1"]["image"] == "ghcr.io/nokia/srlinux:26.3.2"
        assert node_by_id["client1"]["kind"] == "linux"

        cli_by_device = {
            item["device_id"]: item
            for item in payload["cli_access"]
        }

        assert "sr_cli" in cli_by_device["srl1"]["command"]
        assert cli_by_device["client1"]["command"].endswith(" sh")

        topology_file = generated_dir / "lab.clab.yml"
        assert topology_file.exists()
        assert "nokia_srlinux" in topology_file.read_text(encoding="utf-8")
    finally:
        if generated_dir.exists():
            shutil.rmtree(generated_dir)

