import shutil
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.enums import SessionStatus
from app.services import session_service
from app.services.session_service import update_session_status
from app.services.topology_generator import GENERATED_DIR


client = TestClient(app)

STUDENT_AUTH_HEADERS = {"Authorization": "Bearer demo-student-token"}
INSTRUCTOR_AUTH_HEADERS = {"Authorization": "Bearer demo-instructor-token"}


def _unique_student_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


def _remove_runtime_file_metadata(session_id: str) -> None:
    session_service._sessions.pop(session_id, None)
    shutil.rmtree(GENERATED_DIR / session_id, ignore_errors=True)


def _create_historical_session(student_id: str, difficulty: str = "easy") -> str:
    create_response = client.post(
        "/api/v1/labs",
        json={
            "student_id": student_id,
            "difficulty": difficulty,
            "topology_template": "basic-two-router",
        },
    )

    assert create_response.status_code == 201
    session_id = create_response.json()["session_id"]

    update_session_status(session_id, SessionStatus.destroyed)
    _remove_runtime_file_metadata(session_id)

    return session_id


def test_labs_list_reads_database_when_session_json_is_absent():
    student_id = _unique_student_id("sprint29-db-first-history-student")
    session_id = _create_historical_session(student_id=student_id, difficulty="hard")

    response = client.get(
        f"/api/v1/labs?student_id={student_id}&limit=50",
        headers=INSTRUCTOR_AUTH_HEADERS,
    )

    assert response.status_code == 200

    payload = response.json()
    session_ids = [session["session_id"] for session in payload["sessions"]]

    assert session_id in session_ids
    assert payload["count"] >= 1

    listed_session = next(
        session
        for session in payload["sessions"]
        if session["session_id"] == session_id
    )

    assert listed_session["student_id"] == student_id
    assert listed_session["status"] == "destroyed"
    assert "topology_summary" in listed_session
    assert "topology" in listed_session
    assert "cli_access" in listed_session

    serialized = str(listed_session).lower()
    assert "injected_errors" not in serialized
    assert "evidence" not in serialized
    assert "runtime_cleanup_history" not in serialized


def test_get_lab_uses_database_fallback_when_session_json_is_absent():
    student_id = _unique_student_id("sprint29-db-first-detail-student")
    session_id = _create_historical_session(student_id=student_id, difficulty="medium")

    response = client.get(
        f"/api/v1/labs/{session_id}",
        headers=INSTRUCTOR_AUTH_HEADERS,
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["session_id"] == session_id
    assert payload["student_id"] == student_id
    assert payload["status"] == "destroyed"
    assert "injected_errors" not in payload
    assert "runtime_cleanup_history" not in payload


def test_labs_list_does_not_duplicate_database_and_generated_metadata():
    student_id = _unique_student_id("sprint29-db-first-dedup-student")

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

    response = client.get(
        f"/api/v1/labs?student_id={student_id}&limit=50",
        headers=INSTRUCTOR_AUTH_HEADERS,
    )

    assert response.status_code == 200

    session_ids = [
        session["session_id"]
        for session in response.json()["sessions"]
    ]

    assert session_ids.count(session_id) == 1


def test_student_labs_list_uses_authenticated_username_as_owner():
    own_session_id = _create_historical_session(
        student_id="student",
        difficulty="easy",
    )
    other_session_id = _create_historical_session(
        student_id=_unique_student_id("sprint29-other-student"),
        difficulty="easy",
    )

    response = client.get(
        "/api/v1/labs?limit=200",
        headers=STUDENT_AUTH_HEADERS,
    )

    assert response.status_code == 200

    sessions = response.json()["sessions"]
    session_ids = [session["session_id"] for session in sessions]

    assert own_session_id in session_ids
    assert other_session_id not in session_ids
    assert all(session["student_id"] == "student" for session in sessions)


def test_instructor_labs_student_id_filter_reads_database_history():
    student_id = _unique_student_id("sprint29-db-first-instructor-filter-student")
    session_id = _create_historical_session(student_id=student_id, difficulty="hard")

    response = client.get(
        f"/api/v1/labs?student_id={student_id}&limit=200",
        headers=INSTRUCTOR_AUTH_HEADERS,
    )

    assert response.status_code == 200

    sessions = response.json()["sessions"]
    session_ids = [session["session_id"] for session in sessions]

    assert session_id in session_ids
    assert all(session["student_id"] == student_id for session in sessions)


def test_db_only_active_status_does_not_block_new_lab_creation():
    student_id = _unique_student_id("sprint29-db-only-active-student")

    first_response = client.post(
        "/api/v1/labs",
        json={
            "student_id": student_id,
            "difficulty": "easy",
            "topology_template": "basic-two-router",
        },
    )

    assert first_response.status_code == 201
    first_session_id = first_response.json()["session_id"]

    _remove_runtime_file_metadata(first_session_id)

    second_response = client.post(
        "/api/v1/labs",
        json={
            "student_id": student_id,
            "difficulty": "easy",
            "topology_template": "basic-two-router",
        },
    )

    assert second_response.status_code == 201
    assert second_response.json()["session_id"] != first_session_id
