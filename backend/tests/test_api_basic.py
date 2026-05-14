from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.services.containerlab_adapter import GENERATED_DIR, containerlab_adapter


client = TestClient(app)

STUDENT_AUTH_HEADERS = {"Authorization": "Bearer demo-student-token"}
INSTRUCTOR_AUTH_HEADERS = {"Authorization": "Bearer demo-instructor-token"}


def test_health_endpoint_returns_ok():
    response = client.get("/api/v1/health")

    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "AutoNetLab Backend API"


def test_create_lab_medium_returns_success():
    response = client.post(
        "/api/v1/labs",
        json={
            "student_id": "pytest-student",
            "difficulty": "medium",
            "topology_template": "basic-two-router",
        },
    )

    assert response.status_code == 201

    data = response.json()
    assert data["success"] is True
    assert data["student_id"] == "pytest-student"
    assert data["difficulty"] == "medium"
    assert data["status"] == "created"
    assert "injected_errors" not in data
    assert "hints" in data
    assert len(data["hints"]) >= 1
    assert len(data["cli_access"]) >= 1

def test_get_lab_default_response_is_student_safe():
    create_response = client.post(
        "/api/v1/labs",
        json={
            "student_id": "pytest-student",
            "difficulty": "medium",
            "topology_template": "basic-two-router",
        },
    )

    assert create_response.status_code == 201

    session_id = create_response.json()["session_id"]

    get_response = client.get(f"/api/v1/labs/{session_id}")

    assert get_response.status_code == 200

    data = get_response.json()
    assert data["success"] is True
    assert data["session_id"] == session_id
    assert "topology" in data
    assert "cli_access" in data
    assert "hints" in data
    assert "injected_errors" not in data
    assert "expected_fix" not in data
    assert "solution" not in data
    assert "answer" not in data
    assert "debug" not in data

def test_get_lab_debug_response_includes_injected_errors():
    create_response = client.post(
        "/api/v1/labs",
        json={
            "student_id": "pytest-student",
            "difficulty": "medium",
            "topology_template": "basic-two-router",
        },
    )

    assert create_response.status_code == 201

    session_id = create_response.json()["session_id"]

    debug_response = client.get(
        f"/api/v1/labs/{session_id}/debug",
        headers=INSTRUCTOR_AUTH_HEADERS,
    )

    assert debug_response.status_code == 200

    data = debug_response.json()
    assert data["success"] is True
    assert data["session_id"] == session_id
    assert "injected_errors" in data
    assert len(data["injected_errors"]) == 3
    assert "hints" in data


def test_get_unknown_lab_returns_standard_error():
    response = client.get("/api/v1/labs/lab-does-not-exist")

    assert response.status_code == 404

    data = response.json()
    assert data["success"] is False
    assert data["error_code"] == "LAB_SESSION_NOT_FOUND"
    assert "suggestion" in data


def test_get_unknown_cli_returns_standard_error():
    response = client.get("/api/v1/labs/lab-does-not-exist/cli")

    assert response.status_code == 404

    data = response.json()
    assert data["success"] is False
    assert data["error_code"] == "LAB_SESSION_NOT_FOUND"
    assert data["path"] == "/api/v1/labs/lab-does-not-exist/cli"


def test_invalid_difficulty_returns_standard_error():
    response = client.post(
        "/api/v1/labs",
        json={
            "student_id": "pytest-student",
            "difficulty": "impossible",
            "topology_template": "basic-two-router",
        },
    )

    assert response.status_code == 422

    data = response.json()
    assert data["success"] is False
    assert data["error_code"] == "INVALID_DIFFICULTY"
    assert data["suggestion"] == "Use one of the supported values: easy, medium, hard."


def test_validate_created_lab_returns_validation_result():
    create_response = client.post(
        "/api/v1/labs",
        json={
            "student_id": "pytest-student",
            "difficulty": "easy",
            "topology_template": "basic-two-router",
        },
    )

    assert create_response.status_code == 201

    session_id = create_response.json()["session_id"]

    validate_response = client.post(f"/api/v1/labs/{session_id}/validate")

    assert validate_response.status_code == 200

    data = validate_response.json()
    assert data["success"] is True
    assert data["session_id"] == session_id
    assert data["status"] == "validated"
    assert "score" in data
    assert "checks" in data
    assert "recommendations" in data


def test_containerlab_not_found_returns_frontend_friendly_error(monkeypatch):
    test_session_id = "lab-pytest-missing-clab"
    test_dir = GENERATED_DIR / test_session_id
    test_dir.mkdir(parents=True, exist_ok=True)

    topology_file = test_dir / "lab.clab.yml"
    topology_file.write_text(
        """
name: autonetlab-lab-pytest-missing-clab
topology:
  nodes:
    r1:
      kind: linux
      image: alpine:latest
""".strip(),
        encoding="utf-8",
    )

    def fake_which(command_name: str):
        if command_name == "containerlab":
            return None

        return f"/usr/bin/{command_name}"

    monkeypatch.setattr(
        "app.services.containerlab_adapter.shutil.which",
        fake_which,
    )

    result = containerlab_adapter.deploy(
        session_id=test_session_id,
        topology_file=str(topology_file),
    )

    assert result["success"] is False
    assert result["status"] == "error"
    assert result["error_code"] == "CONTAINERLAB_NOT_FOUND"
    assert "suggestion" in result
def test_instructor_analytics_endpoints_after_validation():
    create_response = client.post(
        "/api/v1/labs",
        json={
            "student_id": "analytics-student",
            "difficulty": "medium",
            "topology_template": "basic-two-router",
        },
    )

    assert create_response.status_code == 201

    session_id = create_response.json()["session_id"]

    validate_response = client.post(f"/api/v1/labs/{session_id}/validate")

    assert validate_response.status_code == 200

    summary_response = client.get(
        "/api/v1/instructor/analytics/summary",
        headers=INSTRUCTOR_AUTH_HEADERS,
    )
    assert summary_response.status_code == 200

    summary = summary_response.json()
    assert summary["success"] is True
    assert summary["total_sessions"] >= 1
    assert summary["completed_sessions"] >= 1
    assert "average_score" in summary
    assert "pass_rate" in summary

    distribution_response = client.get(
        "/api/v1/instructor/analytics/difficulty-distribution",
        headers=INSTRUCTOR_AUTH_HEADERS,
    )
    assert distribution_response.status_code == 200

    distribution = distribution_response.json()
    assert distribution["success"] is True
    assert isinstance(distribution["distribution"], list)
    assert any(item["difficulty"] == "medium" for item in distribution["distribution"])

    weaknesses_response = client.get(
        "/api/v1/instructor/analytics/topic-weaknesses",
        headers=INSTRUCTOR_AUTH_HEADERS,
    )
    assert weaknesses_response.status_code == 200

    weaknesses = weaknesses_response.json()
    assert weaknesses["success"] is True
    assert isinstance(weaknesses["topic_weaknesses"], list)

    recent_response = client.get(
        "/api/v1/instructor/sessions/recent",
        headers=INSTRUCTOR_AUTH_HEADERS,
    )
    assert recent_response.status_code == 200

    recent = recent_response.json()
    assert recent["success"] is True
    assert isinstance(recent["recent_sessions"], list)
    assert any(item["session_id"] == session_id for item in recent["recent_sessions"])



def test_recommendations_endpoint_before_validation_returns_empty_state():
    create_response = client.post(
        "/api/v1/labs",
        json={
            "student_id": "recommendation-student",
            "difficulty": "easy",
            "topology_template": "basic-two-router",
        },
    )

    assert create_response.status_code == 201

    session_id = create_response.json()["session_id"]

    recommendation_response = client.get(f"/api/v1/labs/{session_id}/recommendations")

    assert recommendation_response.status_code == 200

    data = recommendation_response.json()
    assert data["success"] is True
    assert data["session_id"] == session_id
    assert data["source"] == "rule_based"
    assert data["fallback_used"] is True
    assert data["recommendations"] == []
    assert "Run validation" in data["message"]


def test_recommendations_endpoint_after_validation_returns_explanatory_items():
    create_response = client.post(
        "/api/v1/labs",
        json={
            "student_id": "recommendation-student",
            "difficulty": "medium",
            "topology_template": "basic-two-router",
        },
    )

    assert create_response.status_code == 201

    session_id = create_response.json()["session_id"]

    validate_response = client.post(f"/api/v1/labs/{session_id}/validate")
    assert validate_response.status_code == 200

    recommendation_response = client.get(f"/api/v1/labs/{session_id}/recommendations")
    assert recommendation_response.status_code == 200

    data = recommendation_response.json()
    assert data["success"] is True
    assert data["session_id"] == session_id
    assert data["source"] in ["rule_based", "ml_prototype", "hybrid"]
    assert isinstance(data["fallback_used"], bool)
    assert isinstance(data["recommendations"], list)
    assert len(data["recommendations"]) >= 1

    first_item = data["recommendations"][0]
    assert "topic" in first_item
    assert "label" in first_item
    assert "reason" in first_item
    assert "explanation" in first_item
    assert first_item["priority"] in ["low", "medium", "high"]
    assert 0 <= first_item["confidence"] <= 1
    assert first_item["source"] in ["rule_based", "ml_prototype", "hybrid"]
    assert isinstance(first_item["next_actions"], list)
    assert isinstance(first_item["related_failed_checks"], list)


def test_validation_persists_topic_performance_for_ml_ready_history():
    import json

    create_response = client.post(
        "/api/v1/labs",
        json={
            "student_id": "ml-ready-student",
            "difficulty": "easy",
            "topology_template": "basic-two-router",
        },
    )

    assert create_response.status_code == 201

    session_id = create_response.json()["session_id"]

    validate_response = client.post(f"/api/v1/labs/{session_id}/validate")
    assert validate_response.status_code == 200

    metadata_path = GENERATED_DIR / session_id / "session.json"
    assert metadata_path.exists()

    payload = json.loads(metadata_path.read_text(encoding="utf-8"))

    assert "topic_performance" in payload
    assert isinstance(payload["topic_performance"], list)
    assert len(payload["topic_performance"]) >= 1

    first_topic = payload["topic_performance"][0]
    assert "topic" in first_topic
    assert "attempt_count" in first_topic
    assert "fail_count" in first_topic
    assert "failure_rate" in first_topic

def test_sprint8_validation_checks_include_advanced_fields():
    response = client.post(
        "/api/v1/labs",
        json={
            "student_id": "sprint8-validation-student",
            "difficulty": "hard",
            "topology_template": "basic-two-router",
        },
    )

    assert response.status_code == 201

    session_id = response.json()["session_id"]

    validate_response = client.post(f"/api/v1/labs/{session_id}/validate")
    assert validate_response.status_code == 200

    data = validate_response.json()

    assert data["success"] is True
    assert data["status"] == "validated"
    assert len(data["checks"]) == 5

    allowed_topics = {
        "ip_addressing",
        "subnetting",
        "interface_status",
        "default_gateway",
        "static_routing",
        "vlan_like",
        "acl_like",
        "connectivity",
    }

    for check in data["checks"]:
        assert "check_id" in check
        assert check["topic"] in allowed_topics
        assert "description" in check
        assert check["status"] in ["passed", "failed", "warning", "skipped"]
        assert "passed" in check
        assert "points" in check
        assert "max_points" in check
        assert "message" in check
        assert "hint" in check
        assert "evidence" in check
        assert isinstance(check["evidence"], dict)
        assert check["evidence"]["validation_mode"] == "config_marker_check"


def test_sprint8_cli_access_response_includes_mode_info():
    response = client.post(
        "/api/v1/labs",
        json={
            "student_id": "sprint8-cli-student",
            "difficulty": "easy",
            "topology_template": "basic-two-router",
        },
    )

    assert response.status_code == 201

    session_id = response.json()["session_id"]

    cli_response = client.get(f"/api/v1/labs/{session_id}/cli")
    assert cli_response.status_code == 200

    data = cli_response.json()

    assert data["success"] is True
    assert data["current_mode"] == "local_docker_exec_demo"
    assert data["mode_info"]["current_mode"] == "local_docker_exec_demo"
    assert "ssh_gateway_planned" in data["mode_info"]["planned_modes"]
    assert "browser_cli_future_work" in data["mode_info"]["planned_modes"]

    assert len(data["devices"]) >= 1

    for device in data["devices"]:
        assert device["access_method"] == "docker_exec"
        assert device["mode"] == "local_docker_exec_demo"
        assert device["command"].startswith("docker exec -it")


def test_sprint8_cli_access_modes_metadata_endpoint():
    response = client.get("/api/v1/meta/cli-access-modes")

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert data["current_mode"] == "local_docker_exec_demo"
    assert data["default_mode"] == "local_docker_exec_demo"

    modes_by_value = {
        item["value"]: item
        for item in data["modes"]
    }

    assert modes_by_value["local_docker_exec_demo"]["status"] == "active"
    assert modes_by_value["ssh_gateway_planned"]["status"] == "planned"
    assert modes_by_value["browser_cli_future_work"]["status"] == "future_work"
    assert "Sprint 8 keeps docker exec local demo mode" in data["decision"]



def test_sprint9_auth_login_student_returns_demo_token():
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "student",
            "password": "student123",
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["access_token"] == "demo-student-token"
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "student"
    assert data["user"]["role"] == "student"
    assert data["user"]["student_id"] == "demo-student"


def test_sprint9_auth_login_instructor_returns_demo_token():
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "instructor",
            "password": "instructor123",
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["access_token"] == "demo-instructor-token"
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "instructor"
    assert data["user"]["role"] == "instructor"
    assert data["user"]["student_id"] is None


def test_sprint9_auth_login_rejects_invalid_credentials():
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "student",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401


def test_sprint9_auth_me_returns_current_user():
    response = client.get(
        "/api/v1/auth/me",
        headers=STUDENT_AUTH_HEADERS,
    )

    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["user"]["username"] == "student"
    assert data["user"]["role"] == "student"


def test_sprint9_auth_me_requires_token():
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_sprint9_instructor_endpoints_require_instructor_role():
    no_auth_response = client.get("/api/v1/instructor/analytics/summary")
    assert no_auth_response.status_code == 401

    student_response = client.get(
        "/api/v1/instructor/analytics/summary",
        headers=STUDENT_AUTH_HEADERS,
    )
    assert student_response.status_code == 403

    instructor_response = client.get(
        "/api/v1/instructor/analytics/summary",
        headers=INSTRUCTOR_AUTH_HEADERS,
    )
    assert instructor_response.status_code == 200


def test_sprint9_debug_lab_endpoint_requires_instructor_role():
    create_response = client.post(
        "/api/v1/labs",
        json={
            "student_id": "sprint9-debug-student",
            "difficulty": "easy",
            "topology_template": "basic-two-router",
        },
    )

    assert create_response.status_code == 201

    session_id = create_response.json()["session_id"]

    no_auth_response = client.get(f"/api/v1/labs/{session_id}/debug")
    assert no_auth_response.status_code == 401

    student_response = client.get(
        f"/api/v1/labs/{session_id}/debug",
        headers=STUDENT_AUTH_HEADERS,
    )
    assert student_response.status_code == 403

    instructor_response = client.get(
        f"/api/v1/labs/{session_id}/debug",
        headers=INSTRUCTOR_AUTH_HEADERS,
    )
    assert instructor_response.status_code == 200
    assert "injected_errors" in instructor_response.json()


def test_sprint10_instructor_students_endpoint_requires_instructor_role():
    no_auth_response = client.get("/api/v1/instructor/students")
    assert no_auth_response.status_code == 401

    student_response = client.get(
        "/api/v1/instructor/students",
        headers=STUDENT_AUTH_HEADERS,
    )
    assert student_response.status_code == 403

    instructor_response = client.get(
        "/api/v1/instructor/students",
        headers=INSTRUCTOR_AUTH_HEADERS,
    )
    assert instructor_response.status_code == 200

    data = instructor_response.json()
    assert data["success"] is True
    assert "students" in data
    assert isinstance(data["students"], list)


def test_sprint10_instructor_student_detail_endpoints_return_student_history():
    student_id = "sprint10-dashboard-student"

    create_response = client.post(
        "/api/v1/labs",
        json={
            "student_id": student_id,
            "difficulty": "medium",
            "topology_template": "basic-two-router",
        },
    )

    assert create_response.status_code == 201

    session_id = create_response.json()["session_id"]

    validate_response = client.post(f"/api/v1/labs/{session_id}/validate")
    assert validate_response.status_code == 200

    students_response = client.get(
        "/api/v1/instructor/students",
        headers=INSTRUCTOR_AUTH_HEADERS,
    )
    assert students_response.status_code == 200

    students_data = students_response.json()
    assert any(
        item["student_id"] == student_id
        for item in students_data["students"]
    )

    summary_response = client.get(
        f"/api/v1/instructor/students/{student_id}/summary",
        headers=INSTRUCTOR_AUTH_HEADERS,
    )
    assert summary_response.status_code == 200

    summary = summary_response.json()
    assert summary["success"] is True
    assert summary["student_id"] == student_id
    assert summary["total_sessions"] >= 1
    assert summary["completed_sessions"] >= 1
    assert "average_score" in summary
    assert "pass_rate" in summary
    assert "first_seen_at" in summary
    assert "last_activity_at" in summary

    sessions_response = client.get(
        f"/api/v1/instructor/students/{student_id}/sessions",
        headers=INSTRUCTOR_AUTH_HEADERS,
    )
    assert sessions_response.status_code == 200

    sessions_data = sessions_response.json()
    assert sessions_data["success"] is True
    assert sessions_data["student_id"] == student_id
    assert isinstance(sessions_data["sessions"], list)
    assert any(
        item["session_id"] == session_id
        for item in sessions_data["sessions"]
    )

    weaknesses_response = client.get(
        f"/api/v1/instructor/students/{student_id}/topic-weaknesses",
        headers=INSTRUCTOR_AUTH_HEADERS,
    )
    assert weaknesses_response.status_code == 200

    weaknesses_data = weaknesses_response.json()
    assert weaknesses_data["success"] is True
    assert weaknesses_data["student_id"] == student_id
    assert isinstance(weaknesses_data["topic_weaknesses"], list)

    trend_response = client.get(
        f"/api/v1/instructor/students/{student_id}/score-trend",
        headers=INSTRUCTOR_AUTH_HEADERS,
    )
    assert trend_response.status_code == 200

    trend_data = trend_response.json()
    assert trend_data["success"] is True
    assert trend_data["student_id"] == student_id
    assert isinstance(trend_data["score_trend"], list)
    assert any(
        item["session_id"] == session_id
        for item in trend_data["score_trend"]
    )
