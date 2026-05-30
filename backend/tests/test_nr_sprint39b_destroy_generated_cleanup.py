import shutil
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.enums import SessionStatus
from app.services import session_service
from app.services.containerlab_adapter import GENERATED_DIR, containerlab_adapter
from app.services.scenario_catalog import (
    CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID,
    SR_BASIC_LINK_SCENARIO_ID,
)
from app.services.session_service import (
    get_lab_session,
    remove_generated_session_folder,
    update_session_status,
)


client = TestClient(app)


def _successful_destroy_action(session_id: str) -> dict:
    return {
        "success": True,
        "session_id": session_id,
        "status": SessionStatus.destroyed,
        "message": "Containerlab topology destroyed successfully.",
        "command": "containerlab destroy -t lab.clab.yml",
        "return_code": 0,
        "stdout": "",
        "stderr": "",
        "error_code": None,
        "detail": None,
        "suggestion": None,
    }


def _topology_missing_destroy_action(session_id: str) -> dict:
    return {
        "success": False,
        "session_id": session_id,
        "status": SessionStatus.error,
        "message": "Topology YAML file could not be found.",
        "command": "containerlab destroy -t missing-lab.clab.yml",
        "return_code": None,
        "stdout": "",
        "stderr": "",
        "error_code": "TOPOLOGY_FILE_NOT_FOUND",
        "detail": "Topology file not found.",
        "suggestion": "Create the lab session again or check generated metadata.",
    }


def _create_lab(student_prefix: str, scenario_id: str) -> str:
    response = client.post(
        "/api/v1/labs",
        json={
            "student_id": f"{student_prefix}-{uuid4().hex[:8]}",
            "difficulty": "easy",
            "scenario_id": scenario_id,
        },
    )

    assert response.status_code == 201
    return response.json()["session_id"]


def test_nr_sprint39b_destroy_removes_generated_folder_after_success(monkeypatch):
    session_id = _create_lab(
        student_prefix="nr39b-folder-cleanup",
        scenario_id=SR_BASIC_LINK_SCENARIO_ID,
    )
    session_dir = GENERATED_DIR / session_id

    assert session_dir.exists()

    monkeypatch.setattr(
        "app.api.routes.labs.containerlab_adapter.destroy",
        lambda session_id, topology_file: _successful_destroy_action(session_id),
    )

    response = client.post(f"/api/v1/labs/{session_id}/destroy")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["status"] == "destroyed"
    assert not session_dir.exists()

    refreshed = get_lab_session(session_id)
    assert refreshed["status"] == SessionStatus.destroyed


def test_nr_sprint39b_destroy_folder_cleanup_is_idempotent_when_folder_missing(monkeypatch):
    session_id = _create_lab(
        student_prefix="nr39b-folder-missing",
        scenario_id=SR_BASIC_LINK_SCENARIO_ID,
    )
    session_dir = GENERATED_DIR / session_id

    shutil.rmtree(session_dir)
    assert not session_dir.exists()

    monkeypatch.setattr(
        "app.api.routes.labs.containerlab_adapter.destroy",
        lambda session_id, topology_file: _successful_destroy_action(session_id),
    )

    response = client.post(f"/api/v1/labs/{session_id}/destroy")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["status"] == "destroyed"
    assert not session_dir.exists()


def test_nr_sprint39b_historical_db_only_destroy_still_removes_recreated_metadata_folder(monkeypatch):
    session_id = _create_lab(
        student_prefix="nr39b-historical-db-only",
        scenario_id=SR_BASIC_LINK_SCENARIO_ID,
    )
    session_dir = GENERATED_DIR / session_id

    update_session_status(session_id, SessionStatus.error)
    shutil.rmtree(session_dir)
    session_service._sessions.pop(session_id, None)

    monkeypatch.setattr(
        containerlab_adapter,
        "runtime_containers_exist",
        lambda session: False,
    )

    response = client.post(f"/api/v1/labs/{session_id}/destroy")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["status"] == "destroyed"
    assert payload["error_code"] is None
    assert "already complete" in payload["message"]
    assert not session_dir.exists()

    refreshed = get_lab_session(session_id)
    assert refreshed["status"] == SessionStatus.destroyed


def test_nr_sprint39b_srl_basic_link_destroy_regression(monkeypatch):
    session_id = _create_lab(
        student_prefix="nr39b-srl-basic",
        scenario_id=SR_BASIC_LINK_SCENARIO_ID,
    )
    session_dir = GENERATED_DIR / session_id

    monkeypatch.setattr(
        "app.api.routes.labs.containerlab_adapter.destroy",
        lambda session_id, topology_file: _successful_destroy_action(session_id),
    )

    response = client.post(f"/api/v1/labs/{session_id}/destroy")

    assert response.status_code == 200
    assert response.json()["status"] == "destroyed"
    assert not session_dir.exists()


def test_nr_sprint39b_campus_destroy_regression(monkeypatch):
    session_id = _create_lab(
        student_prefix="nr39b-campus",
        scenario_id=CAMPUS_CORE_STATIC_ROUTING_SCENARIO_ID,
    )
    session_dir = GENERATED_DIR / session_id

    monkeypatch.setattr(
        "app.api.routes.labs.containerlab_adapter.destroy",
        lambda session_id, topology_file: _successful_destroy_action(session_id),
    )

    response = client.post(f"/api/v1/labs/{session_id}/destroy")

    assert response.status_code == 200
    assert response.json()["status"] == "destroyed"
    assert not session_dir.exists()


def test_nr_sprint39b_generated_folder_cleanup_rejects_unsafe_session_id():
    result = remove_generated_session_folder("../lab-unsafe")

    assert result["success"] is False
    assert result["removed"] is False
    assert result["error_code"] == "UNSAFE_GENERATED_SESSION_ID"

def test_nr_sprint39b_destroy_is_idempotent_for_destroyed_session_with_session_json_only(monkeypatch):
    session_id = _create_lab(
        student_prefix="nr39b-destroyed-session-json-only",
        scenario_id=SR_BASIC_LINK_SCENARIO_ID,
    )
    session_dir = GENERATED_DIR / session_id
    topology_file = session_dir / "lab.clab.yml"
    metadata_path = session_dir / "session.json"

    assert topology_file.exists()
    assert metadata_path.exists()

    update_session_status(session_id, SessionStatus.destroyed)
    topology_file.unlink()

    assert not topology_file.exists()
    assert metadata_path.exists()

    monkeypatch.setattr(
        "app.api.routes.labs.containerlab_adapter.destroy",
        lambda session_id, topology_file: _topology_missing_destroy_action(session_id),
    )
    monkeypatch.setattr(
        containerlab_adapter,
        "runtime_containers_exist",
        lambda session: False,
    )

    response = client.post(f"/api/v1/labs/{session_id}/destroy")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["status"] == "destroyed"
    assert payload["error_code"] is None
    assert "already complete" in payload["message"]
    assert not session_dir.exists()

    refreshed = get_lab_session(session_id)
    assert refreshed["status"] == SessionStatus.destroyed
