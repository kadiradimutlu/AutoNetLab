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

    Sprint 3:
    - Executes real Containerlab commands through subprocess/alt süreç.
    - Supports deploy/ayağa kaldırma, destroy/kapatma, inspect/durum kontrolü.
    - Never executes raw user-provided terminal commands.
    - Validates topology path to reduce path traversal risk.
    - Performs basic preflight checks:
      containerlab installed, Docker reachable, topology file exists.
    """

    def deploy(self, session_id: str, topology_file: str) -> dict:
        topology_path = self._resolve_topology_file(topology_file)

        return self._run_containerlab_command(
            session_id=session_id,
            action="deploy",
            command=["containerlab", "deploy", "-t", str(topology_path)],
            success_status=SessionStatus.deployed,
            success_message="Containerlab topology deployed successfully.",
            timeout_seconds=180,
        )

    def destroy(self, session_id: str, topology_file: str) -> dict:
        topology_path = self._resolve_topology_file(topology_file)

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
        topology_path = self._resolve_topology_file(topology_file)

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
                message=(
                    "Containerlab command not found. Run the backend from WSL/Ubuntu "
                    "or install containerlab in the current environment."
                ),
                stderr="containerlab executable was not found.",
            )
        except PermissionError as exc:
            return self._error_response(
                session_id=session_id,
                action=action,
                command=command,
                message="Permission denied while running Containerlab command.",
                stderr=str(exc),
            )
        except subprocess.TimeoutExpired as exc:
            return self._error_response(
                session_id=session_id,
                action=action,
                command=command,
                message=f"Containerlab {action} command timed out after {timeout_seconds} seconds.",
                stdout=exc.stdout or "",
                stderr=exc.stderr or "",
            )

        is_success = completed.returncode == 0

        if not is_success:
            return self._error_response(
                session_id=session_id,
                action=action,
                command=command,
                message=self._build_failure_message(action, completed.stderr),
                return_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
            )

        return {
            "session_id": session_id,
            "status": success_status,
            "message": success_message,
            "command": self._format_command(command),
            "return_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
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
                message=(
                    "Containerlab is not available in the current backend environment. "
                    "For this project, run uvicorn inside WSL/Ubuntu where containerlab is installed."
                ),
                stderr=(
                    "containerlab executable was not found in PATH. "
                    f"Detected OS: {platform.system()}"
                ),
            )

        if shutil.which("docker") is None:
            return self._error_response(
                session_id=session_id,
                action=action,
                command=command,
                message="Docker command is not available in the current backend environment.",
                stderr="docker executable was not found in PATH.",
            )

        docker_check = subprocess.run(
            ["docker", "info"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        if docker_check.returncode != 0:
            return self._error_response(
                session_id=session_id,
                action=action,
                command=command,
                message=(
                    "Docker is not reachable. Make sure Docker Desktop is running "
                    "and WSL integration is enabled."
                ),
                return_code=docker_check.returncode,
                stdout=docker_check.stdout,
                stderr=docker_check.stderr,
            )

        return None

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

    def _build_failure_message(self, action: str, stderr: str | None) -> str:
        normalized_stderr = (stderr or "").lower()

        if "permission denied" in normalized_stderr:
            return (
                f"Containerlab {action} failed because of a permission problem. "
                "Try running the backend from WSL/Ubuntu with proper Docker permissions."
            )

        if "cannot connect to the docker daemon" in normalized_stderr:
            return (
                "Containerlab could not connect to Docker. "
                "Make sure Docker Desktop is running and WSL integration is enabled."
            )

        if "not found" in normalized_stderr:
            return (
                f"Containerlab {action} failed because a required file, image, "
                "or command was not found."
            )

        return f"Containerlab {action} command failed."

    def _error_response(
        self,
        session_id: str,
        action: str,
        command: list[str],
        message: str,
        return_code: int | None = None,
        stdout: str = "",
        stderr: str = "",
    ) -> dict:
        return {
            "session_id": session_id,
            "status": SessionStatus.error,
            "message": message,
            "command": self._format_command(command),
            "return_code": return_code,
            "stdout": stdout,
            "stderr": stderr,
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