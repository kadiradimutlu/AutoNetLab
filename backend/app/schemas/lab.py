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
    name: str = Field(..., examples=["r1"])
    container_name: str = Field(..., examples=["clab-autonetlab-lab-12345678-r1"])
    access_method: str = Field(default="docker_exec", examples=["docker_exec"])
    command: str = Field(..., examples=["docker exec -it clab-autonetlab-lab-12345678-r1 sh"])
    description: str = Field(
        ...,
        examples=["R1 cihazına CLI üzerinden bağlanmak için bu komutu kullanın."],
    )


class CliAccessResponse(BaseModel):
    success: bool = True
    session_id: str
    lab_name: str
    devices: list[CliAccess]
    message: str


class LabSessionResponse(BaseModel):
    success: bool = True
    session_id: str
    student_id: str
    difficulty: Difficulty
    status: SessionStatus
    topology: Topology
    injected_errors: list[ErrorItem]
    cli_access: list[CliAccess]
    message: str


class ActionResponse(BaseModel):
    success: bool = True
    session_id: str
    status: SessionStatus
    message: str
    command: str | None = None
    return_code: int | None = None
    stdout: str | None = None
    stderr: str | None = None

    # Sprint 4 API polish / API cilalama fields
    error_code: str | None = None
    detail: str | None = None
    suggestion: str | None = None