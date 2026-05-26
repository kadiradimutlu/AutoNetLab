from fastapi.testclient import TestClient

from app.main import app
from app.schemas.enums import SessionStatus
from app.services.session_service import update_session_status


client = TestClient(app)

STUDENT_AUTH_HEADERS = {"Authorization": "Bearer demo-student-token"}


def test_sprint26_validation_history_stores_each_attempt_student_safe():
    create_response = client.post(
        "/api/v1/labs",
        json={
            "student_id": "sprint26-history-student",
            "difficulty": "medium",
            "topology_template": "basic-two-router",
        },
    )

    assert create_response.status_code == 201
    session_id = create_response.json()["session_id"]

    assert client.post(f"/api/v1/labs/{session_id}/validate").status_code == 200
    assert client.post(f"/api/v1/labs/{session_id}/validate").status_code == 200

    history_response = client.get(f"/api/v1/labs/{session_id}/validation-history")

    assert history_response.status_code == 200

    history = history_response.json()
    assert history["session_id"] == session_id
    assert [attempt["attempt_number"] for attempt in history["attempts"]] == [1, 2]

    for attempt in history["attempts"]:
        assert attempt["passed_checks"] + attempt["failed_checks"] == len(attempt["checks"])
        assert attempt["created_at"]

        for check in attempt["checks"]:
            assert "evidence" not in check
            assert "injection_commands" not in check


def test_sprint26_validated_lab_is_runtime_active_for_web_cli_readiness(monkeypatch):
    create_response = client.post(
        "/api/v1/labs",
        json={
            "student_id": "demo-student",
            "difficulty": "easy",
            "topology_template": "basic-two-router",
        },
    )

    assert create_response.status_code == 201
    session_id = create_response.json()["session_id"]

    update_session_status(session_id, SessionStatus.validated)

    monkeypatch.setattr(
        "app.services.web_cli_service.shutil.which",
        lambda command_name: "/usr/bin/docker" if command_name == "docker" else None,
    )

    class FakeCompletedProcess:
        returncode = 0
        stdout = "true\n"
        stderr = ""

    monkeypatch.setattr(
        "app.services.web_cli_service.subprocess.run",
        lambda *args, **kwargs: FakeCompletedProcess(),
    )

    response = client.get(
        f"/api/v1/labs/{session_id}/cli/readiness/r1",
        headers=STUDENT_AUTH_HEADERS,
    )

    assert response.status_code == 200

    data = response.json()
    assert data["lab_status"] == "validated"
    assert data["lab_deployed"] is True
    assert data["ready"] is True


def test_sprint26_one_active_lab_per_student_then_destroyed_allows_new_lab():
    student_id = "sprint26-active-student"

    first_response = client.post(
        "/api/v1/labs",
        json={
            "student_id": student_id,
            "difficulty": "easy",
            "topology_template": "basic-two-router",
        },
    )

    assert first_response.status_code == 201
    active_session_id = first_response.json()["session_id"]

    conflict_response = client.post(
        "/api/v1/labs",
        json={
            "student_id": student_id,
            "difficulty": "medium",
            "topology_template": "basic-two-router",
        },
    )

    assert conflict_response.status_code == 409

    conflict_payload = conflict_response.json()
    assert conflict_payload["error_code"] == "ACTIVE_LAB_ALREADY_EXISTS"
    assert conflict_payload["active_session_id"] == active_session_id

    update_session_status(active_session_id, SessionStatus.destroyed)

    next_response = client.post(
        "/api/v1/labs",
        json={
            "student_id": student_id,
            "difficulty": "hard",
            "topology_template": "basic-two-router",
        },
    )

    assert next_response.status_code == 201


def test_sprint26_finish_closes_runtime_but_preserves_validation_history(monkeypatch):
    student_id = "sprint26-finish-student"

    create_response = client.post(
        "/api/v1/labs",
        json={
            "student_id": student_id,
            "difficulty": "easy",
            "topology_template": "basic-two-router",
        },
    )

    assert create_response.status_code == 201
    session_id = create_response.json()["session_id"]

    assert client.post(f"/api/v1/labs/{session_id}/validate").status_code == 200

    def fake_destroy(session_id: str, topology_file: str) -> dict:
        return {
            "success": True,
            "session_id": session_id,
            "status": SessionStatus.destroyed,
            "message": "Containerlab topology destroyed successfully.",
            "command": "containerlab destroy -t fake",
            "return_code": 0,
            "stdout": "",
            "stderr": "",
            "error_code": None,
            "detail": None,
            "suggestion": None,
        }

    monkeypatch.setattr(
        "app.api.routes.labs.containerlab_adapter.destroy",
        fake_destroy,
    )

    finish_response = client.post(f"/api/v1/labs/{session_id}/finish")

    assert finish_response.status_code == 200

    finish_payload = finish_response.json()
    assert finish_payload["status"] == "finished"
    assert finish_payload["message"] == "Lab finished successfully. Validation history is preserved."

    history_response = client.get(f"/api/v1/labs/{session_id}/validation-history")
    assert history_response.status_code == 200
    assert len(history_response.json()["attempts"]) == 1

    get_response = client.get(f"/api/v1/labs/{session_id}")
    assert get_response.status_code == 200
    assert get_response.json()["status"] == "finished"
    assert get_response.json()["finished_at"] is not None

    next_response = client.post(
        "/api/v1/labs",
        json={
            "student_id": student_id,
            "difficulty": "medium",
            "topology_template": "basic-two-router",
        },
    )

    assert next_response.status_code == 201


def test_sprint26_hints_endpoint_returns_student_safe_guidance():
    create_response = client.post(
        "/api/v1/labs",
        json={
            "student_id": "sprint26-hints-student",
            "difficulty": "hard",
            "topology_template": "basic-two-router",
        },
    )

    assert create_response.status_code == 201
    session_id = create_response.json()["session_id"]

    hints_response = client.get(f"/api/v1/labs/{session_id}/hints")

    assert hints_response.status_code == 200

    data = hints_response.json()
    assert data["success"] is True
    assert data["session_id"] == session_id
    assert len(data["hints"]) >= 1

    serialized = str(data).lower()
    assert "injection_commands" not in serialized
    assert "expected_outputs" not in serialized
    assert "ip route replace" not in serialized
    assert "ip link set" not in serialized

    for hint in data["hints"]:
        assert hint["level"] == "general"
        assert hint["message"]



def test_sprint26_validation_attempts_are_persisted_to_database():
    from app.db.models import ValidationAttemptRecord
    from app.db.session import session_scope

    create_response = client.post(
        "/api/v1/labs",
        json={
            "student_id": "sprint26-db-attempt-student",
            "difficulty": "medium",
            "topology_template": "basic-two-router",
        },
    )

    assert create_response.status_code == 201
    session_id = create_response.json()["session_id"]

    assert client.post(f"/api/v1/labs/{session_id}/validate").status_code == 200
    assert client.post(f"/api/v1/labs/{session_id}/validate").status_code == 200

    with session_scope() as db:
        attempts = (
            db.query(ValidationAttemptRecord)
            .filter(ValidationAttemptRecord.session_id == session_id)
            .order_by(ValidationAttemptRecord.attempt_number.asc())
            .all()
        )

        assert [attempt.attempt_number for attempt in attempts] == [1, 2]
        assert all(attempt.score >= 0 for attempt in attempts)
        assert all(attempt.raw_result_json for attempt in attempts)
