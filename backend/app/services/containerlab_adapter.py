from app.schemas.enums import SessionStatus


class ContainerlabAdapter:
    """
    Adapter layer for Containerlab runtime commands.

    Sprint 1 MVP:
    - This class does not run real containerlab commands yet.
    - It returns mock responses.
    - Later, subprocess.run() can be used to call:
      containerlab deploy -t ...
      containerlab destroy -t ...
    """

    def deploy(self, session_id: str, topology_name: str) -> dict:
        return {
            "session_id": session_id,
            "status": SessionStatus.deployed,
            "message": f"MOCK: Topology '{topology_name}' deployed successfully.",
        }

    def destroy(self, session_id: str, topology_name: str) -> dict:
        return {
            "session_id": session_id,
            "status": SessionStatus.destroyed,
            "message": f"MOCK: Topology '{topology_name}' destroyed successfully.",
        }


containerlab_adapter = ContainerlabAdapter()