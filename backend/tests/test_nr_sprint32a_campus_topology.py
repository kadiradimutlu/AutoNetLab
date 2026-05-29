import shutil
from pathlib import Path
from uuid import uuid4

import yaml
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.enums import Difficulty
from app.services.scenario_catalog import (
    CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID,
    get_scenario,
    is_deploy_only_scenario,
    list_scenarios,
)
from app.services.topology_generator import GENERATED_DIR, generate_session_topology


client = TestClient(app)


def _new_student(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


def test_nr_sprint32a_catalog_exposes_campus_core_static_routing():
    scenarios = list_scenarios()
    scenario_by_id = {scenario["id"]: scenario for scenario in scenarios}

    scenario = scenario_by_id[CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID]

    assert scenario["title"] == "Campus Core Static Routing"
    assert scenario["topology_template"] == "campus-core-static-routing"
    assert scenario["router_os"] == "Nokia SR Linux"
    assert scenario["runtime_profile"] == "deploy_only"
    assert is_deploy_only_scenario(CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID) is True

    devices = {device["id"]: device for device in scenario["devices"]}
    assert set(devices) == {"client1", "client2", "srl1", "srl2", "srl3", "srl4"}
    assert devices["client1"]["role"] == "client"
    assert devices["client2"]["role"] == "client"
    assert devices["srl1"]["role"] == "edge_router"
    assert devices["srl2"]["role"] == "edge_router"
    assert devices["srl3"]["role"] == "core_router"
    assert devices["srl4"]["role"] == "core_router"
    assert len(scenario["links"]) == 6
    assert scenario["addressing_table"]


def test_nr_sprint32a_generate_campus_topology_file():
    session_id = "lab-nr32a-campus-test"
    generated_dir = GENERATED_DIR / session_id

    if generated_dir.exists():
        shutil.rmtree(generated_dir)

    try:
        result = generate_session_topology(
            session_id=session_id,
            difficulty=Difficulty.easy,
            topology_template="campus-core-static-routing",
            scenario_id=CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID,
        )

        topology = result["topology"]
        topology_file = Path(result["topology_file"])

        assert result["topology_template"] == "campus-core-static-routing"
        assert topology_file.exists()
        assert len(topology.nodes) == 6
        assert len(topology.links) == 6

        node_by_id = {node.id: node for node in topology.nodes}
        assert set(node_by_id) == {"client1", "client2", "srl1", "srl2", "srl3", "srl4"}
        assert node_by_id["client1"].kind == "linux"
        assert node_by_id["client1"].role == "client"
        assert node_by_id["client2"].kind == "linux"
        assert node_by_id["client2"].role == "client"
        assert node_by_id["srl1"].kind == "nokia_srlinux"
        assert node_by_id["srl1"].role == "edge_router"
        assert node_by_id["srl3"].role == "core_router"

        payload = yaml.safe_load(topology_file.read_text(encoding="utf-8"))

        nodes = payload["topology"]["nodes"]
        links = payload["topology"]["links"]

        assert set(nodes) == {"client1", "client2", "srl1", "srl2", "srl3", "srl4"}
        assert nodes["srl1"]["kind"] == "nokia_srlinux"
        assert nodes["srl1"]["type"] == "ixr-d2l"
        assert nodes["client1"]["kind"] == "linux"
        assert len(links) == 6
        assert links[0]["endpoints"] == ["client1:eth1", "srl1:e1-1"]
        assert links[1]["endpoints"] == ["srl1:e1-2", "srl3:e1-1"]
        assert links[2]["endpoints"] == ["srl3:e1-2", "srl2:e1-2"]
        assert links[3]["endpoints"] == ["srl2:e1-1", "client2:eth1"]
        assert links[4]["endpoints"] == ["srl1:e1-3", "srl4:e1-1"]
        assert links[5]["endpoints"] == ["srl4:e1-2", "srl2:e1-3"]
    finally:
        if generated_dir.exists():
            shutil.rmtree(generated_dir)


def test_nr_sprint32a_create_lab_returns_student_safe_campus_contract():
    response = client.post(
        "/api/v1/labs",
        json={
            "student_id": _new_student("nr32a-campus"),
            "difficulty": "easy",
            "scenario_id": CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID,
        },
    )

    assert response.status_code == 201

    payload = response.json()

    assert payload["success"] is True
    assert payload["scenario"]["id"] == CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID
    assert payload["scenario"]["title"] == "Campus Core Static Routing"
    assert payload["topology_summary"]["node_count"] == 6
    assert payload["topology_summary"]["link_count"] == 6
    assert payload["topology_summary"]["devices"] == [
        "client1",
        "srl1",
        "srl3",
        "srl2",
        "client2",
        "srl4",
    ]

    nodes = {node["id"]: node for node in payload["topology"]["nodes"]}
    assert nodes["client1"]["role"] == "client"
    assert nodes["client2"]["role"] == "client"
    assert nodes["srl1"]["role"] == "edge_router"
    assert nodes["srl3"]["role"] == "core_router"

    links = payload["topology"]["links"]
    assert len(links) == 6
    assert links[0]["source"] == {"node": "client1", "interface": "eth1"}
    assert links[0]["target"] == {"node": "srl1", "interface": "e1-1"}

    cli_access = {item["device_id"]: item for item in payload["cli_access"]}
    assert set(cli_access) == {"client1", "client2", "srl1", "srl2", "srl3", "srl4"}
    assert cli_access["srl1"]["command"].endswith(" sr_cli")
    assert cli_access["srl4"]["command"].endswith(" sr_cli")
    assert cli_access["client1"]["command"].endswith(" sh")
    assert cli_access["client2"]["command"].endswith(" sh")

    forbidden_keys = {
        "injected_errors",
        "evidence",
        "debug",
        "solution",
        "validation_command",
        "injection_commands",
    }
    assert forbidden_keys.isdisjoint(payload.keys())


def test_nr_sprint32a_meta_scenarios_api_includes_campus_scenario():
    response = client.get("/api/v1/meta/scenarios")

    assert response.status_code == 200

    payload = response.json()
    scenario_by_id = {scenario["id"]: scenario for scenario in payload["scenarios"]}

    assert CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID in scenario_by_id
    assert scenario_by_id[CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID]["title"] == (
        "Campus Core Static Routing"
    )


def test_nr_sprint32a_deploy_only_campus_does_not_run_runtime_setup(monkeypatch):
    create_response = client.post(
        "/api/v1/labs",
        json={
            "student_id": _new_student("nr32a-campus-deploy"),
            "difficulty": "easy",
            "scenario_id": CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID,
        },
    )
    assert create_response.status_code == 201
    session_id = create_response.json()["session_id"]

    def fake_deploy(session_id: str, topology_file: str):
        return {
            "success": True,
            "session_id": session_id,
            "status": "deployed",
            "message": "Containerlab topology deployed successfully.",
            "command": "containerlab deploy -t lab.clab.yml",
            "return_code": 0,
            "stdout": "",
            "stderr": "",
            "error_code": None,
            "detail": None,
            "suggestion": None,
        }

    def fail_if_called(*args, **kwargs):
        raise AssertionError("Runtime setup or runtime fault injection should not run for deploy-only campus scenario.")

    monkeypatch.setattr("app.api.routes.labs.containerlab_adapter.deploy", fake_deploy)
    monkeypatch.setattr("app.api.routes.labs.apply_srlinux_runtime_setup", fail_if_called)
    monkeypatch.setattr("app.api.routes.labs.apply_runtime_error_injection", fail_if_called)

    deploy_response = client.post(f"/api/v1/labs/{session_id}/deploy")

    assert deploy_response.status_code == 200

    payload = deploy_response.json()
    assert payload["success"] is True
    assert payload["status"] == "deployed"
    assert "foundation mode without runtime fault injection" in payload["message"]
