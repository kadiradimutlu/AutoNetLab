from pathlib import Path
import subprocess

from fastapi import HTTPException, status

from app.schemas.enums import SessionStatus


PROJECT_ROOT = Path(__file__).resolve().parents[3]
GENERATED_DIR = PROJECT_ROOT / "containerlab" / "generated"
TEMPLATES_DIR = PROJECT_ROOT / "containerlab" / "templates"


class ContainerlabAdapter:
    """
    Containerlab Adapter / Containerlab Adaptörü.

    Sprint 2:
    - Real containerlab commands are executed with subprocess/alt süreç.
    - User input is not used as a raw terminal command.
    - Only safe backend-defined actions are supported:
      deploy/ayağa kaldırma, destroy/kapatma, inspect/durum kontrolü.
    """

    def deploy(self, session_id: str, topology_file: str) -> dict:
        topology_path = self._resolve_topology_file(topology_file)

        return self._run_containerlab_command(
            session_id=session_id,
            action="deploy",
            command=["containerlab", "deploy", "-t", str(topology_path)],
            success_status=SessionStatus.deployed,
            success_message="Containerlab topology deployed successfully.",
            timeout_seconds=120,
        )

    def destroy(self, session_id: str, topology_file: str) -> dict:
        topology_path = self._resolve_topology_file(topology_file)

        return self._run_containerlab_command(
            session_id=session_id,
            action="destroy",
            command=["containerlab", "destroy", "-t", str(topology_path)],
            success_status=SessionStatus.destroyed,
            success_message="Containerlab topology destroyed successfully.",
            timeout_seconds=120,
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
            timeout_seconds=60,
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
            return {
                "session_id": session_id,
                "status": SessionStatus.error,
                "message": "Containerlab command not found. Check that containerlab is installed in WSL/Ubuntu.",
                "command": self._format_command(command),
                "return_code": None,
                "stdout": "",
                "stderr": "containerlab executable was not found.",
            }
        except subprocess.TimeoutExpired as exc:
            return {
                "session_id": session_id,
                "status": SessionStatus.error,
                "message": f"Containerlab {action} command timed out after {timeout_seconds} seconds.",
                "command": self._format_command(command),
                "return_code": None,
                "stdout": exc.stdout or "",
                "stderr": exc.stderr or "",
            }

        is_success = completed.returncode == 0

        return {
            "session_id": session_id,
            "status": success_status if is_success else SessionStatus.error,
            "message": success_message if is_success else f"Containerlab {action} command failed.",
            "command": self._format_command(command),
            "return_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }

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

    @staticmethod
    def _is_child_of(child: Path, parent: Path) -> bool:
        try:
            child.relative_to(parent)
            return True
        except ValueError:
            return False

    @staticmethod
    def _format_command(command: list[str]) -> str:
        return " ".join(command)


containerlab_adapter = ContainerlabAdapter()
