from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _new_student(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


def test_sprint32b_create_without_scenario_defaults_to_srlinux():
    response = client.post(
        "/api/v1/labs",
        json={
            "student_id": _new_student("sprint32b-default"),
            "difficulty": "easy",
        },
    )

    assert response.status_code == 201

    payload = response.json()

    assert payload["success"] is True
    assert payload["scenario"]["id"] == "srl-edge-link"
    assert payload["topology_summary"]["node_count"] == 2
    assert payload["topology_summary"]["link_count"] == 1
    assert set(payload["topology_summary"]["devices"]) == {"srl1", "client1"}

    node_kinds = {
        node["id"]: node["kind"]
        for node in payload["topology"]["nodes"]
    }
    assert node_kinds == {
        "srl1": "nokia_srlinux",
        "client1": "linux",
    }

    cli_commands = {
        item["device_id"]: item["command"]
        for item in payload["cli_access"]
    }
    assert "sr_cli" in cli_commands["srl1"]
    assert cli_commands["client1"].endswith(" sh")

    forbidden_keys = {
        "injected_errors",
        "evidence",
        "debug",
        "solution",
        "validation_command",
        "injection_commands",
    }
    assert forbidden_keys.isdisjoint(payload.keys())


def test_sprint32b_legacy_topology_template_is_ignored_for_new_create_flow():
    response = client.post(
        "/api/v1/labs",
        json={
            "student_id": _new_student("sprint32b-legacy"),
            "difficulty": "hard",
            "scenario_id": "srl-edge-link",
        },
    )

    assert response.status_code == 201

    payload = response.json()

    assert payload["scenario"]["id"] == "srl-edge-link"
    assert set(payload["topology_summary"]["devices"]) == {"srl1", "client1"}
    assert {
        node["id"]
        for node in payload["topology"]["nodes"]
    } == {"srl1", "client1"}


def test_sprint32b_unknown_scenario_is_still_rejected():
    response = client.post(
        "/api/v1/labs",
        json={
            "student_id": _new_student("sprint32b-unknown"),
            "difficulty": "easy",
            "scenario_id": "unknown-scenario",
        },
    )

    assert response.status_code == 400
    assert "Unsupported scenario_id" in response.text
