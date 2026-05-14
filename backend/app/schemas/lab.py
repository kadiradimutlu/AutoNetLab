from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.enums import Difficulty, SessionStatus
from app.schemas.topology import Topology


CliAccessMode = Literal[
    "local_docker_exec_demo",
    "ssh_gateway_planned",
    "browser_cli_future_work",
]


class CreateLabRequest(BaseModel):
    student_id: str = Field(..., examples=["kadir"])
    difficulty: Difficulty = Field(default=Difficulty.easy, examples=["easy"])
    topology_template: str = Field(default="basic-two-router", examples=["basic-two-router"])


class ErrorItem(BaseModel):
    code: str = Field(..., examples=["VLAN_MISMATCH"])
    topic: str = Field(..., examples=["vlan_like"])
    device: str = Field(..., examples=["r1"])
    description: str = Field(..., examples=["VLAN-like mismatch on interface eth1"])
    severity: str = Field(..., examples=["medium"])


class CliAccess(BaseModel):
    device_id: str = Field(..., examples=["r1"])
    name: str = Field(..., examples=["r1"])
    container_name: str = Field(..., examples=["clab-autonetlab-lab-12345678-r1"])
    access_method: str = Field(default="docker_exec", examples=["docker_exec"])
    mode: CliAccessMode = Field(
        default="local_docker_exec_demo",
        examples=["local_docker_exec_demo"],
    )
    command: str = Field(..., examples=["docker exec -it clab-autonetlab-lab-12345678-r1 sh"])
    description: str = Field(
        ...,
        examples=["R1 cihazına CLI üzerinden bağlanmak için bu komutu kullanın."],
    )


class CliAccessModeInfo(BaseModel):
    current_mode: CliAccessMode = Field(
        default="local_docker_exec_demo",
        examples=["local_docker_exec_demo"],
    )
    default_mode: CliAccessMode = Field(
        default="local_docker_exec_demo",
        examples=["local_docker_exec_demo"],
    )
    planned_modes: list[CliAccessMode] = Field(
        default_factory=lambda: [
            "ssh_gateway_planned",
            "browser_cli_future_work",
        ],
        examples=[["ssh_gateway_planned", "browser_cli_future_work"]],
    )
    decision: str = Field(
        default=(
            "Sprint 8 keeps docker exec local demo mode as the stable CLI access model. "
            "SSH Gateway and Browser-based CLI are documented as future work."
        )
    )
    reason: str = Field(
        default=(
            "The project prioritizes stable validation, scenario quality, and demo reliability. "
            "Browser-based CLI and SSH Gateway add security, session isolation, and terminal streaming complexity."
        )
    )


class CliAccessResponse(BaseModel):
    success: bool = True
    session_id: str
    lab_name: str
    current_mode: CliAccessMode = Field(
        default="local_docker_exec_demo",
        examples=["local_docker_exec_demo"],
    )
    mode_info: CliAccessModeInfo = Field(default_factory=CliAccessModeInfo)
    devices: list[CliAccess]
    message: str


class LabSessionResponse(BaseModel):
    """
    Student-safe lab session response / öğrenciye güvenli lab oturumu yanıtı.

    This response is safe for the student dashboard.
    It intentionally does not include injected_errors, expected fixes,
    solution data, answer data, or internal debug fields.
    """

    success: bool = True
    session_id: str
    student_id: str
    difficulty: Difficulty
    status: SessionStatus
    topology: Topology
    cli_access: list[CliAccess]
    hints: list[str] = Field(
        default_factory=list,
        examples=[
            [
                "Check IP addressing and subnet masks.",
                "Verify interface status before testing connectivity.",
                "Review routing and default gateway configuration.",
            ]
        ],
    )
    message: str


class LabSessionDebugResponse(LabSessionResponse):
    """
    Instructor/debug lab session response / eğitmen veya debug lab oturumu yanıtı.

    This response keeps injected_errors visible for debugging,
    instructor review, and backend development purposes.
    It must not be used by the student-facing frontend screen.
    """

    injected_errors: list[ErrorItem]


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