from pydantic import BaseModel, Field

from app.schemas.enums import Difficulty, SessionStatus
from app.schemas.topology import Topology


class CreateLabRequest(BaseModel):
    student_id: str = Field(..., examples=["kadir"])
    difficulty: Difficulty = Field(default=Difficulty.easy, examples=["easy"])
    topology_template: str = Field(default="basic-two-router", examples=["basic-two-router"])


class ErrorItem(BaseModel):
    code: str = Field(..., examples=["VLAN_MISMATCH"])
    topic: str = Field(..., examples=["VLAN"])
    device: str = Field(..., examples=["r1"])
    description: str = Field(..., examples=["VLAN ID mismatch on interface eth1"])
    severity: str = Field(..., examples=["low"])


class CliAccess(BaseModel):
    device_id: str = Field(..., examples=["r1"])
    command: str = Field(..., examples=["docker exec -it clab-autonetlab-r1 sh"])


class LabSessionResponse(BaseModel):
    session_id: str
    student_id: str
    difficulty: Difficulty
    status: SessionStatus
    topology: Topology
    injected_errors: list[ErrorItem]
    cli_access: list[CliAccess]
    message: str


class ActionResponse(BaseModel):
    session_id: str
    status: SessionStatus
    message: str
    command: str | None = None
    return_code: int | None = None
    stdout: str | None = None
    stderr: str | None = None