from fastapi.testclient import TestClient

from app.main import app
from app.schemas.enums import SessionStatus
from app.services.containerlab_adapter import GENERATED_DIR, containerlab_adapter
from app.services.session_service import get_lab_session, update_session_status


client = TestClient(app)


def _successful_action(session_id: str, status: SessionStatus, message: str) -> dict:
    return {
        "success": True,
        "session_id": session_id,
        "status": status,
        "message": message,
        "command": "containerlab test command",
        "return_code": 0,
        "stdout": "",
        "stderr": "",
        "error_code": None,
        "detail": None,
        "suggestion": None,
    }


def _failed_runtime_action(session_id: str) -> dict:
    return {
        "success": False,
        "session_id": session_id,
        "status": SessionStatus.error,
        "message": "Containerlab deployed, but runtime error injection failed.",
        "command": "docker exec runtime baseline and injected error commands",
        "return_code": 1,
        "stdout": "",
        "stderr": "forced runtime setup failure",
        "error_code": "RUNTIME_ERROR_INJECTION_COMMAND_FAILED",
        "detail": "Runtime injection command failed for r1.",
        "suggestion": "Destroy the lab and create a new session.",
    }


def test_deploy_runtime_failure_attempts_best_effort_cleanup(monkeypatch):
    create_response = client.post(
        "/api/v1/labs",
        json={
            "student_id": "sprint29-runtime-cleanup-student",
            "difficulty": "hard",
            "topology_template": "basic-two-router",
        },
    )
    assert create_response.status_code == 201
    session_id = create_response.json()["session_id"]

    cleanup_calls = []

    def fake_deploy(session_id: str, topology_file: str) -> dict:
        return _successful_action(
            session_id=session_id,
            status=SessionStatus.deployed,
            message="Containerlab topology deployed successfully.",
        )

    def fake_runtime_error_injection(session: dict) -> dict:
        return _failed_runtime_action(str(session["session_id"]))

    def fake_destroy(session_id: str, topology_file: str) -> dict:
        cleanup_calls.append((session_id, topology_file))
        return _successful_action(
            session_id=session_id,
            status=SessionStatus.destroyed,
            message="Containerlab topology destroyed successfully.",
        )

    monkeypatch.setattr("app.api.routes.labs.containerlab_adapter.deploy", fake_deploy)
    monkeypatch.setattr("app.api.routes.labs.apply_runtime_error_injection", fake_runtime_error_injection)
    monkeypatch.setattr("app.api.routes.labs.containerlab_adapter.destroy", fake_destroy)

    deploy_response = client.post(f"/api/v1/labs/{session_id}/deploy")
    assert deploy_response.status_code == 200

    payload = deploy_response.json()
    assert payload["success"] is False
    assert payload["status"] == "error"
    assert payload["error_code"] == "RUNTIME_ERROR_INJECTION_COMMAND_FAILED"
    assert "Runtime cleanup" in payload["stderr"]

    session = get_lab_session(session_id)
    assert cleanup_calls == [(session_id, session["topology_file"])]
    assert session["status"] == SessionStatus.error
    assert session["runtime_cleanup_history"][-1]["trigger"] == "runtime_setup_failed_after_deploy"
    assert session["runtime_cleanup_history"][-1]["success"] is True

    serialized_payload = str(payload).lower()
    assert "injected_errors" not in serialized_payload
    assert "evidence" not in serialized_payload


def test_error_state_destroy_marks_session_destroyed(monkeypatch):
    create_response = client.post(
        "/api/v1/labs",
        json={
            "student_id": "sprint29-error-destroy-student",
            "difficulty": "easy",
            "topology_template": "basic-two-router",
        },
    )
    assert create_response.status_code == 201
    session_id = create_response.json()["session_id"]

    update_session_status(session_id, SessionStatus.error)

    def fake_destroy(session_id: str, topology_file: str) -> dict:
        return _successful_action(
            session_id=session_id,
            status=SessionStatus.destroyed,
            message="Containerlab topology destroyed successfully.",
        )

    monkeypatch.setattr("app.api.routes.labs.containerlab_adapter.destroy", fake_destroy)

    destroy_response = client.post(f"/api/v1/labs/{session_id}/destroy")
    assert destroy_response.status_code == 200

    payload = destroy_response.json()
    assert payload["success"] is True
    assert payload["status"] == "destroyed"

    get_response = client.get(f"/api/v1/labs/{session_id}")
    assert get_response.status_code == 200
    assert get_response.json()["status"] == "destroyed"


def test_destroy_is_idempotent_when_runtime_is_already_absent(monkeypatch):
    session_id = "lab-sprint29-already-clean"
    session_dir = GENERATED_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    topology_file = session_dir / "lab.clab.yml"
    topology_file.write_text(
        """
name: autonetlab-lab-sprint29-already-clean
topology:
  nodes:
    r1:
      kind: linux
      image: alpine:latest
""".strip(),
        encoding="utf-8",
    )

    class FakeCompletedProcess:
        returncode = 1
        stdout = ""
        stderr = "no containers found"

    monkeypatch.setattr(
        containerlab_adapter,
        "_run_preflight_checks",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "app.services.containerlab_adapter.subprocess.run",
        lambda *args, **kwargs: FakeCompletedProcess(),
    )

    result = containerlab_adapter.destroy(
        session_id=session_id,
        topology_file=str(topology_file),
    )

    assert result["success"] is True
    assert result["status"] == SessionStatus.destroyed
    assert result["return_code"] == 1
    assert result["error_code"] is None
    assert "already destroyed" in result["message"]


def test_finish_error_state_lab_cleans_runtime_and_finishes(monkeypatch):
    create_response = client.post(
        "/api/v1/labs",
        json={
            "student_id": "sprint29-error-finish-student",
            "difficulty": "medium",
            "topology_template": "basic-two-router",
        },
    )
    assert create_response.status_code == 201
    session_id = create_response.json()["session_id"]

    update_session_status(session_id, SessionStatus.error)

    def fake_destroy(session_id: str, topology_file: str) -> dict:
        return _successful_action(
            session_id=session_id,
            status=SessionStatus.destroyed,
            message="Containerlab topology destroyed successfully.",
        )

    monkeypatch.setattr("app.api.routes.labs.containerlab_adapter.destroy", fake_destroy)

    finish_response = client.post(f"/api/v1/labs/{session_id}/finish")
    assert finish_response.status_code == 200

    payload = finish_response.json()
    assert payload["success"] is True
    assert payload["status"] == "finished"

    session = get_lab_session(session_id)
    assert session["status"] == SessionStatus.finished
    assert session["finished_at"] is not None
