from pathlib import Path
import platform
import shlex
import shutil
import subprocess

from fastapi import HTTPException, status

from app.schemas.enums import SessionStatus


PROJECT_ROOT = Path(__file__).resolve().parents[3]
GENERATED_DIR = PROJECT_ROOT / "containerlab" / "generated"
TEMPLATES_DIR = PROJECT_ROOT / "containerlab" / "templates"


class ContainerlabAdapter:
    """
    Containerlab Adapter / Containerlab Adaptörü.

    Sprint 4 goal:
    - Keep deploy/ayağa kaldırma, inspect/durum kontrolü and destroy/kapatma stable.
    - Prevent backend crash when Containerlab, Docker or topology execution fails.
    - Return frontend-friendly JSON error responses.
    """

    def deploy(self, session_id: str, topology_file: str) -> dict:
        topology_path = self._resolve_or_error(
            session_id=session_id,
            action="deploy",
            topology_file=topology_file,
        )

        if isinstance(topology_path, dict):
            return topology_path

        return self._run_containerlab_command(
            session_id=session_id,
            action="deploy",
            command=["containerlab", "deploy", "-t", str(topology_path)],
            success_status=SessionStatus.deployed,
            success_message="Containerlab topology deployed successfully.",
            timeout_seconds=180,
        )

    def destroy(self, session_id: str, topology_file: str) -> dict:
        topology_path = self._resolve_or_error(
            session_id=session_id,
            action="destroy",
            topology_file=topology_file,
        )

        if isinstance(topology_path, dict):
            return topology_path

        return self._run_containerlab_command(
            session_id=session_id,
            action="destroy",
            command=["containerlab", "destroy", "-t", str(topology_path)],
            success_status=SessionStatus.destroyed,
            success_message="Containerlab topology destroyed successfully.",
            timeout_seconds=180,
        )

    def inspect(
        self,
        session_id: str,
        topology_file: str,
        current_status: SessionStatus,
    ) -> dict:
        topology_path = self._resolve_or_error(
            session_id=session_id,
            action="inspect",
            topology_file=topology_file,
        )

        if isinstance(topology_path, dict):
            return topology_path

        return self._run_containerlab_command(
            session_id=session_id,
            action="inspect",
            command=["containerlab", "inspect", "-t", str(topology_path)],
            success_status=current_status,
            success_message="Containerlab topology inspected successfully.",
            timeout_seconds=90,
        )

    def _run_containerlab_command(
        self,
        session_id: str,
        action: str,
        command: list[str],
        success_status: SessionStatus,
        success_message: str,
        timeout_seconds: int,
    ) -> dict:
        preflight_error = self._run_preflight_checks(
            session_id=session_id,
            action=action,
            command=command,
        )

        if preflight_error is not None:
            return preflight_error

        try:
            completed = subprocess.run(
                command,
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
        except FileNotFoundError:
            return self._error_response(
                session_id=session_id,
                action=action,
                command=command,
                error_code="CONTAINERLAB_NOT_FOUND",
                message="Containerlab command could not be found.",
                detail="containerlab executable was not found in PATH.",
                suggestion=(
                    "Run the backend inside WSL/Ubuntu where Containerlab is installed, "
                    "or install Containerlab in the current backend environment."
                ),
            )
        except PermissionError as exc:
            return self._error_response(
                session_id=session_id,
                action=action,
                command=command,
                error_code="CONTAINERLAB_PERMISSION_DENIED",
                message="Permission denied while running Containerlab command.",
                detail=str(exc),
                suggestion=(
                    "Run the backend from WSL/Ubuntu with proper Docker permissions. "
                    "If needed, check Docker group permissions or restart Docker Desktop."
                ),
            )
        except subprocess.TimeoutExpired as exc:
            return self._error_response(
                session_id=session_id,
                action=action,
                command=command,
                error_code=f"CONTAINERLAB_{action.upper()}_TIMEOUT",
                message=f"Containerlab {action} command timed out.",
                detail=f"The command exceeded the timeout limit of {timeout_seconds} seconds.",
                suggestion=(
                    "Check Docker Desktop, WSL integration, image pulling status and system resources. "
                    "Then retry the operation."
                ),
                stdout=exc.stdout or "",
                stderr=exc.stderr or "",
            )

        if completed.returncode != 0:
            if action == "destroy" and self._is_destroy_already_clean(
                stdout=completed.stdout,
                stderr=completed.stderr,
            ):
                return {
                    "success": True,
                    "session_id": session_id,
                    "status": SessionStatus.destroyed,
                    "message": "Containerlab topology was already destroyed; no runtime containers were found.",
                    "command": self._format_command(command),
                    "return_code": completed.returncode,
                    "stdout": completed.stdout,
                    "stderr": completed.stderr,
                    "error_code": None,
                    "detail": None,
                    "suggestion": None,
                }

            failure = self._classify_failure(
                action=action,
                stderr=completed.stderr,
            )

            return self._error_response(
                session_id=session_id,
                action=action,
                command=command,
                error_code=failure["error_code"],
                message=failure["message"],
                detail=failure["detail"],
                suggestion=failure["suggestion"],
                return_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
            )

        return {
            "success": True,
            "session_id": session_id,
            "status": success_status,
            "message": success_message,
            "command": self._format_command(command),
            "return_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "error_code": None,
            "detail": None,
            "suggestion": None,
        }

    def _run_preflight_checks(
        self,
        session_id: str,
        action: str,
        command: list[str],
    ) -> dict | None:
        if shutil.which("containerlab") is None:
            return self._error_response(
                session_id=session_id,
                action=action,
                command=command,
                error_code="CONTAINERLAB_NOT_FOUND",
                message="Containerlab is not available in the current backend environment.",
                detail=(
                    "containerlab executable was not found in PATH. "
                    f"Detected OS: {platform.system()}."
                ),
                suggestion=(
                    "For this project, run uvicorn inside WSL/Ubuntu where Containerlab is installed. "
                    "You can verify it with: containerlab version"
                ),
            )

        if shutil.which("docker") is None:
            return self._error_response(
                session_id=session_id,
                action=action,
                command=command,
                error_code="DOCKER_NOT_FOUND",
                message="Docker command is not available in the current backend environment.",
                detail="docker executable was not found in PATH.",
                suggestion=(
                    "Install Docker Desktop and enable WSL2 integration. "
                    "Then verify it with: docker version"
                ),
            )

        try:
            docker_check = subprocess.run(
                ["docker", "info"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except FileNotFoundError:
            return self._error_response(
                session_id=session_id,
                action=action,
                command=command,
                error_code="DOCKER_NOT_FOUND",
                message="Docker command could not be found.",
                detail="docker executable was not found while running docker info.",
                suggestion="Install Docker Desktop and enable WSL2 integration.",
            )
        except PermissionError as exc:
            return self._error_response(
                session_id=session_id,
                action=action,
                command=command,
                error_code="DOCKER_PERMISSION_DENIED",
                message="Permission denied while checking Docker.",
                detail=str(exc),
                suggestion=(
                    "Check Docker permissions in WSL/Ubuntu. "
                    "You may need to restart Docker Desktop or your WSL session."
                ),
            )
        except subprocess.TimeoutExpired as exc:
            return self._error_response(
                session_id=session_id,
                action=action,
                command=command,
                error_code="DOCKER_CHECK_TIMEOUT",
                message="Docker health check timed out.",
                detail="docker info did not finish within 30 seconds.",
                suggestion=(
                    "Make sure Docker Desktop is running and WSL integration is enabled. "
                    "Then retry the request."
                ),
                stdout=exc.stdout or "",
                stderr=exc.stderr or "",
            )

        if docker_check.returncode != 0:
            return self._error_response(
                session_id=session_id,
                action=action,
                command=command,
                error_code="DOCKER_NOT_RUNNING",
                message="Docker is not reachable.",
                detail=docker_check.stderr or "docker info returned a non-zero exit code.",
                suggestion=(
                    "Start Docker Desktop, enable WSL2 integration, and verify with: docker ps"
                ),
                return_code=docker_check.returncode,
                stdout=docker_check.stdout,
                stderr=docker_check.stderr,
            )

        return None

    def _resolve_or_error(
        self,
        session_id: str,
        action: str,
        topology_file: str,
    ) -> Path | dict:
        command = ["containerlab", action, "-t", str(topology_file)]

        try:
            return self._resolve_topology_file(topology_file)
        except HTTPException as exc:
            if exc.status_code == status.HTTP_404_NOT_FOUND:
                return self._error_response(
                    session_id=session_id,
                    action=action,
                    command=command,
                    error_code="TOPOLOGY_FILE_NOT_FOUND",
                    message="Topology YAML file could not be found.",
                    detail=str(exc.detail),
                    suggestion=(
                        "Create the lab session again or check whether "
                        "containerlab/generated/<session_id>/lab.clab.yml exists."
                    ),
                )

            return self._error_response(
                session_id=session_id,
                action=action,
                command=command,
                error_code="TOPOLOGY_FILE_INVALID",
                message="Topology YAML file is invalid or not allowed.",
                detail=str(exc.detail),
                suggestion=(
                    "Make sure the topology file is a .yml/.yaml file under "
                    "containerlab/generated or containerlab/templates."
                ),
            )

    def _resolve_topology_file(self, topology_file: str) -> Path:
        path = Path(topology_file)

        if not path.is_absolute():
            path = PROJECT_ROOT / path

        resolved_path = path.resolve()

        if not resolved_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Topology file not found: {resolved_path}",
            )

        if resolved_path.suffix not in {".yml", ".yaml"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Topology file must be a YAML file.",
            )

        allowed_roots = [
            GENERATED_DIR.resolve(),
            TEMPLATES_DIR.resolve(),
        ]

        if not any(self._is_child_of(resolved_path, root) for root in allowed_roots):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Topology file path is outside allowed Containerlab directories.",
            )

        return resolved_path

    def _classify_failure(self, action: str, stderr: str | None) -> dict:
        normalized_stderr = (stderr or "").lower()

        if "permission denied" in normalized_stderr:
            return {
                "error_code": "CONTAINERLAB_PERMISSION_DENIED",
                "message": f"Containerlab {action} failed because of a permission problem.",
                "detail": stderr or "Permission denied.",
                "suggestion": (
                    "Run the backend from WSL/Ubuntu with proper Docker permissions. "
                    "Also check Docker Desktop and WSL integration."
                ),
            }

        if (
            "cannot connect to the docker daemon" in normalized_stderr
            or "docker daemon" in normalized_stderr
            or "is the docker daemon running" in normalized_stderr
        ):
            return {
                "error_code": "DOCKER_NOT_RUNNING",
                "message": "Containerlab could not connect to Docker.",
                "detail": stderr or "Docker daemon is not reachable.",
                "suggestion": (
                    "Start Docker Desktop, enable WSL2 integration, and verify with: docker ps"
                ),
            }

        if (
            "pull access denied" in normalized_stderr
            or "manifest unknown" in normalized_stderr
            or "no such image" in normalized_stderr
            or "image" in normalized_stderr and "not found" in normalized_stderr
        ):
            return {
                "error_code": "CONTAINERLAB_MISSING_IMAGE",
                "message": "Required Docker image could not be found or pulled.",
                "detail": stderr or "A required Docker image is missing.",
                "suggestion": (
                    "Check the image name in the topology YAML file and pull it manually if needed. "
                    "Example: docker pull alpine:latest"
                ),
            }

        if (
            "container" in normalized_stderr
            and (
                "not running" in normalized_stderr
                or "exited" in normalized_stderr
                or "unhealthy" in normalized_stderr
            )
        ):
            return {
                "error_code": "CONTAINER_NOT_RUNNING",
                "message": "A Containerlab container did not reach the expected running state.",
                "detail": stderr or "Container state is not running.",
                "suggestion": (
                    "Run containerlab inspect and docker ps -a to identify the failed container."
                ),
            }

        if "not found" in normalized_stderr:
            return {
                "error_code": "CONTAINERLAB_REQUIRED_RESOURCE_NOT_FOUND",
                "message": (
                    f"Containerlab {action} failed because a required file, image, "
                    "or command was not found."
                ),
                "detail": stderr or "Required resource was not found.",
                "suggestion": (
                    "Check the topology YAML path, Docker images, and Containerlab installation."
                ),
            }

        return {
            "error_code": f"CONTAINERLAB_{action.upper()}_FAILED",
            "message": f"Containerlab {action} command failed.",
            "detail": stderr or "Containerlab returned a non-zero exit code.",
            "suggestion": (
                "Check stdout/stderr details, Docker status, WSL integration, and topology YAML."
            ),
        }

    @staticmethod
    def _is_destroy_already_clean(stdout: str | None, stderr: str | None) -> bool:
        combined_output = f"{stdout or ''}\n{stderr or ''}".lower()

        already_clean_markers = (
            "no containers found",
            "no container found",
            "no runtime containers",
            "already destroyed",
            "already removed",
            "does not exist",
            "not found",
            "not running",
        )

        return any(marker in combined_output for marker in already_clean_markers)

    def _error_response(
        self,
        session_id: str,
        action: str,
        command: list[str],
        error_code: str,
        message: str,
        detail: str,
        suggestion: str,
        return_code: int | None = None,
        stdout: str = "",
        stderr: str = "",
    ) -> dict:
        return {
            "success": False,
            "session_id": session_id,
            "status": SessionStatus.error,
            "message": message,
            "command": self._format_command(command),
            "return_code": return_code,
            "stdout": stdout,
            "stderr": stderr,
            "error_code": error_code,
            "detail": detail,
            "suggestion": suggestion,
        }

    @staticmethod
    def _is_child_of(child: Path, parent: Path) -> bool:
        try:
            child.relative_to(parent)
            return True
        except ValueError:
            return False

    @staticmethod
    def _format_command(command: list[str]) -> str:
        return " ".join(shlex.quote(part) for part in command)


containerlab_adapter = ContainerlabAdapter()