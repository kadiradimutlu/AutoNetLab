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
from app.services import containerlab_adapter as containerlab_adapter_module


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


def test_nr_sprint32a_large_topology_uses_extended_deploy_timeout(monkeypatch):
    session_id = "lab-nr32a-timeout-test"
    generated_dir = containerlab_adapter_module.GENERATED_DIR / session_id

    if generated_dir.exists():
        shutil.rmtree(generated_dir)

    generated_dir.mkdir(parents=True, exist_ok=True)
    topology_file = generated_dir / "lab.clab.yml"
    topology_file.write_text(
        yaml.safe_dump(
            {
                "name": f"autonetlab-{session_id}",
                "topology": {
                    "nodes": {
                        "client1": {"kind": "linux", "image": "alpine:latest"},
                        "client2": {"kind": "linux", "image": "alpine:latest"},
                        "srl1": {"kind": "nokia_srlinux", "image": "ghcr.io/nokia/srlinux:26.3.2"},
                        "srl2": {"kind": "nokia_srlinux", "image": "ghcr.io/nokia/srlinux:26.3.2"},
                        "srl3": {"kind": "nokia_srlinux", "image": "ghcr.io/nokia/srlinux:26.3.2"},
                        "srl4": {"kind": "nokia_srlinux", "image": "ghcr.io/nokia/srlinux:26.3.2"},
                    },
                    "links": [],
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    calls = []

    class Completed:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(command, cwd, capture_output, text, timeout, check):
        calls.append({"command": command, "timeout": timeout})
        return Completed()

    monkeypatch.setattr(containerlab_adapter_module.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(containerlab_adapter_module.subprocess, "run", fake_run)

    try:
        result = containerlab_adapter_module.containerlab_adapter.deploy(
            session_id=session_id,
            topology_file=str(topology_file),
        )

        assert result["success"] is True

        deploy_calls = [
            call
            for call in calls
            if call["command"][:2] == ["containerlab", "deploy"]
        ]
        assert len(deploy_calls) == 1
        assert deploy_calls[0]["timeout"] == 600
    finally:
        if generated_dir.exists():
            shutil.rmtree(generated_dir)


def test_nr_sprint32a_deploy_timeout_cleans_partial_runtime(monkeypatch):
    create_response = client.post(
        "/api/v1/labs",
        json={
            "student_id": _new_student("nr32a-campus-timeout-cleanup"),
            "difficulty": "easy",
            "scenario_id": CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID,
        },
    )
    assert create_response.status_code == 201
    session_id = create_response.json()["session_id"]

    calls = {}

    def fake_deploy(session_id: str, topology_file: str):
        return {
            "success": False,
            "session_id": session_id,
            "status": "error",
            "message": "Containerlab deploy command timed out.",
            "command": "containerlab deploy -t lab.clab.yml",
            "return_code": None,
            "stdout": "",
            "stderr": "partial deploy created containers",
            "error_code": "CONTAINERLAB_DEPLOY_TIMEOUT",
            "detail": "The command exceeded the timeout limit.",
            "suggestion": "Check Docker resources.",
        }

    def fake_runtime_containers_exist(session: dict) -> bool:
        calls["runtime_containers_exist"] = session["session_id"]
        return True

    def fake_destroy_runtime_containers(session: dict):
        calls["destroy_runtime_containers"] = session["session_id"]
        return {
            "success": True,
            "session_id": session["session_id"],
            "status": "destroyed",
            "message": "Runtime containers were removed using fallback Docker cleanup.",
            "command": "docker rm -f containers",
            "return_code": 0,
            "stdout": "",
            "stderr": "",
            "error_code": None,
            "detail": None,
            "suggestion": None,
        }

    def fake_record_runtime_cleanup_result(session_id: str, trigger: str, cleanup_result: dict):
        calls["record_runtime_cleanup_result"] = {
            "session_id": session_id,
            "trigger": trigger,
            "cleanup_success": cleanup_result["success"],
        }

    monkeypatch.setattr("app.api.routes.labs.containerlab_adapter.deploy", fake_deploy)
    monkeypatch.setattr(
        "app.api.routes.labs.containerlab_adapter.runtime_containers_exist",
        fake_runtime_containers_exist,
    )
    monkeypatch.setattr(
        "app.api.routes.labs.containerlab_adapter.destroy_runtime_containers",
        fake_destroy_runtime_containers,
    )
    monkeypatch.setattr(
        "app.api.routes.labs.record_runtime_cleanup_result",
        fake_record_runtime_cleanup_result,
    )

    deploy_response = client.post(f"/api/v1/labs/{session_id}/deploy")

    assert deploy_response.status_code == 200

    payload = deploy_response.json()
    assert payload["success"] is False
    assert payload["status"] == "destroyed"
    assert payload["error_code"] == "CONTAINERLAB_DEPLOY_TIMEOUT"
    assert "Partial runtime cleanup completed" in payload["message"]
    assert "Partial runtime cleanup after failed deploy: completed successfully." in payload["stderr"]
    assert calls["runtime_containers_exist"] == session_id
    assert calls["destroy_runtime_containers"] == session_id
    assert calls["record_runtime_cleanup_result"] == {
        "session_id": session_id,
        "trigger": "containerlab_deploy_failed_partial_runtime",
        "cleanup_success": True,
    }
