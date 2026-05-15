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
    assert data["current_mode"] == "browser_cli_mvp"
    assert data["mode_info"]["current_mode"] == "browser_cli_mvp"
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
    assert data["current_mode"] == "browser_cli_mvp"
    assert data["default_mode"] == "browser_cli_mvp"
    assert data["fallback_mode"] == "local_docker_exec_demo_fallback"

    modes_by_value = {
        item["value"]: item
        for item in data["modes"]
    }

    assert modes_by_value["browser_cli_mvp"]["status"] == "active"
    assert modes_by_value["local_docker_exec_demo"]["status"] == "supported"
    assert modes_by_value["local_docker_exec_demo_fallback"]["status"] == "fallback"
    assert modes_by_value["ssh_gateway_planned"]["status"] == "planned"
    assert modes_by_value["browser_cli_future_work"]["status"] == "future_work"
    assert data["websocket"]["path_template"] == "/api/v1/labs/{session_id}/cli/ws/{device_id}"
    assert "Sprint 11 enables browser_cli_mvp" in data["decision"]



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


def test_sprint11_web_cli_requires_auth_token():
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

    with client.websocket_connect(f"/api/v1/labs/{session_id}/cli/ws/r1") as websocket:
        payload = websocket.receive_json()

    assert payload["type"] == "error"
    assert payload["success"] is False
    assert payload["status_code"] == 401
    assert payload["error_code"] == "WEB_CLI_AUTH_REQUIRED"


def test_sprint11_web_cli_blocks_student_from_other_students_session():
    create_response = client.post(
        "/api/v1/labs",
        json={
            "student_id": "another-student",
            "difficulty": "easy",
            "topology_template": "basic-two-router",
        },
    )

    assert create_response.status_code == 201

    session_id = create_response.json()["session_id"]

    with client.websocket_connect(
        f"/api/v1/labs/{session_id}/cli/ws/r1?token=demo-student-token"
    ) as websocket:
        payload = websocket.receive_json()

    assert payload["type"] == "error"
    assert payload["success"] is False
    assert payload["status_code"] == 403
    assert payload["error_code"] == "WEB_CLI_FORBIDDEN"


def test_sprint11_web_cli_requires_deployed_lab_before_runtime_shell():
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

    with client.websocket_connect(
        f"/api/v1/labs/{session_id}/cli/ws/r1?token=demo-student-token"
    ) as websocket:
        payload = websocket.receive_json()

    assert payload["type"] == "error"
    assert payload["success"] is False
    assert payload["status_code"] == 409
    assert payload["error_code"] == "LAB_NOT_DEPLOYED_FOR_WEB_CLI"


def test_sprint11_web_cli_rejects_unknown_device():
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

    with client.websocket_connect(
        f"/api/v1/labs/{session_id}/cli/ws/not-a-device?token=demo-student-token"
    ) as websocket:
        payload = websocket.receive_json()

    assert payload["type"] == "error"
    assert payload["success"] is False
    assert payload["status_code"] == 404
    assert payload["error_code"] == "WEB_CLI_DEVICE_NOT_FOUND"



def test_sprint11_web_cli_context_allows_own_deployed_student_session():
    from app.schemas.enums import SessionStatus
    from app.services.session_service import update_session_status
    from app.services.web_cli_service import build_web_cli_context

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
    update_session_status(session_id, SessionStatus.deployed)

    context = build_web_cli_context(
        session_id=session_id,
        device_id="r1",
        token="demo-student-token",
    )

    assert context.session_id == session_id
    assert context.device_id == "r1"
    assert context.container_name.startswith("clab-")
    assert context.username == "student"
    assert context.role == "student"


def test_sprint12_web_cli_readiness_requires_auth_token():
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

    response = client.get(f"/api/v1/labs/{session_id}/cli/readiness")

    assert response.status_code == 401


def test_sprint12_web_cli_readiness_reports_not_deployed_state():
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

    response = client.get(
        f"/api/v1/labs/{session_id}/cli/readiness",
        headers=STUDENT_AUTH_HEADERS,
    )

    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["session_id"] == session_id
    assert data["current_mode"] == "browser_cli_mvp"
    assert data["lab_status"] == "created"
    assert data["lab_deployed"] is False
    assert data["ready"] is False
    assert data["error_code"] == "LAB_NOT_DEPLOYED_FOR_WEB_CLI"
    assert len(data["devices"]) >= 1
    assert data["devices"][0]["ready"] is False


def test_sprint12_web_cli_device_readiness_rejects_unknown_device():
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

    response = client.get(
        f"/api/v1/labs/{session_id}/cli/readiness/not-a-device",
        headers=STUDENT_AUTH_HEADERS,
    )

    assert response.status_code == 404


def test_sprint12_web_cli_readiness_reports_ready_for_running_container(monkeypatch):
    from app.schemas.enums import SessionStatus
    from app.services.session_service import update_session_status

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
    update_session_status(session_id, SessionStatus.deployed)

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
    assert data["success"] is True
    assert data["session_id"] == session_id
    assert data["lab_deployed"] is True
    assert data["ready"] is True
    assert data["error_code"] is None
    assert len(data["devices"]) == 1
    assert data["devices"][0]["device_id"] == "r1"
    assert data["devices"][0]["container_running"] is True
    assert data["devices"][0]["ready"] is True


def test_sprint13_runtime_readiness_endpoint_returns_environment_status():
    response = client.get("/api/v1/meta/runtime-readiness")

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert "ready" in data
    assert "platform" in data
    assert "recommended_backend_environment" in data
    assert "project_root" in data
    assert "templates_dir_exists" in data
    assert "generated_dir_exists" in data
    assert "docker_available" in data
    assert "docker_ps_ok" in data
    assert "containerlab_available" in data
    assert "current_mode" in data
    assert data["current_mode"] == "browser_cli_mvp"
    assert data["fallback_mode"] == "local_docker_exec_demo_fallback"
    assert isinstance(data["checks"], list)
    assert len(data["checks"]) >= 1


def test_sprint13_runtime_readiness_can_report_ready_environment(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.meta.shutil.which",
        lambda command_name: f"/usr/bin/{command_name}"
        if command_name in {"docker", "containerlab"}
        else None,
    )

    class FakeCompletedProcess:
        def __init__(self, stdout: str):
            self.returncode = 0
            self.stdout = stdout
            self.stderr = ""

    def fake_run(command, *args, **kwargs):
        if command == ["docker", "--version"]:
            return FakeCompletedProcess("Docker version 27.5.1, build 9f9e405\n")

        if command == ["docker", "ps"]:
            return FakeCompletedProcess("CONTAINER ID   IMAGE   COMMAND\n")

        if command == ["containerlab", "version"]:
            return FakeCompletedProcess("version: 0.75.0\n")

        return FakeCompletedProcess("ok\n")

    monkeypatch.setattr(
        "app.api.routes.meta.subprocess.run",
        fake_run,
    )

    response = client.get("/api/v1/meta/runtime-readiness")

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert data["ready"] is True
    assert data["docker_available"] is True
    assert data["docker_ps_ok"] is True
    assert data["containerlab_available"] is True
    assert "Docker version 27.5.1" in data["docker_version"]
    assert "version: 0.75.0" in data["containerlab_version"]

def test_sprint16_database_readiness_endpoint():
    response = client.get("/api/v1/meta/database-readiness")

    assert response.status_code == 200

    payload = response.json()

    assert payload["success"] is True
    assert "ready" in payload
    assert "database_engine" in payload
    assert "database_url" in payload
    assert "message" in payload


def test_sprint16_database_settings_parse_sqlite_default():
    from app.core.config import Settings

    settings = Settings()

    assert settings.database_url
    assert settings.database_url.startswith("sqlite")



def test_sprint16_database_repository_imports():
    from app.db.repositories import (
        persist_lab_session_snapshot,
        persist_recommendation_snapshot,
        persist_validation_result_snapshot,
    )

    assert callable(persist_lab_session_snapshot)
    assert callable(persist_validation_result_snapshot)
    assert callable(persist_recommendation_snapshot)
