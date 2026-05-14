from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.services.containerlab_adapter import GENERATED_DIR, containerlab_adapter


client = TestClient(app)


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
    assert len(data["injected_errors"]) == 3
    assert len(data["cli_access"]) >= 1


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