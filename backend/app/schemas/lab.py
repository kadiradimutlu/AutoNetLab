from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.enums import Difficulty, SessionStatus
from app.schemas.topology import Topology


CliAccessMode = Literal[
    "browser_cli_mvp",
    "local_docker_exec_demo",
    "local_docker_exec_demo_fallback",
    "ssh_gateway_planned",
    "browser_cli_future_work",
]


class CreateLabRequest(BaseModel):
    student_id: str | None = Field(default=None, examples=["kadir"])
    difficulty: Difficulty = Field(default=Difficulty.easy, examples=["easy"])
    topology_template: str | None = Field(
        default=None,
        examples=["srl-basic-link"],
        description=(
            "Deprecated compatibility field. New student-facing lab creation uses scenario_id."
        ),
    )
    scenario_id: str | None = Field(
        default="srl-basic-link",
        examples=["srl-basic-link"],
        description=(
            "Professional network scenario identifier. "
            "The current student-facing flow defaults to the SR Linux basic link scenario."
        ),
    )


class ErrorItem(BaseModel):
    code: str = Field(..., examples=["VLAN_MISMATCH"])
    topic: str = Field(..., examples=["vlan_like"])
    device: str = Field(..., examples=["r1"])
    description: str = Field(..., examples=["VLAN-like mismatch on interface eth1"])
    severity: str = Field(..., examples=["medium"])
    variant_id: str | None = Field(default=None, examples=["r1_eth2_wrong_link_subnet"])
    interface: str | None = Field(default=None, examples=["eth1"])
    validation_command: str | None = Field(default=None, examples=["ip addr show eth1"])
    expected_outputs: list[str] = Field(default_factory=list, examples=[["inet 10.10.12.1/24"]])
    injection_commands: list[str] = Field(default_factory=list, examples=[["ip link set eth1 down"]])


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
        examples=["R1 cihazÄ±na CLI Ã¼zerinden baÄŸlanmak iÃ§in bu komutu kullanÄ±n."],
    )


class CliAccessModeInfo(BaseModel):
    current_mode: CliAccessMode = Field(
        default="browser_cli_mvp",
        examples=["browser_cli_mvp"],
    )
    default_mode: CliAccessMode = Field(
        default="browser_cli_mvp",
        examples=["browser_cli_mvp"],
    )
    planned_modes: list[CliAccessMode] = Field(
        default_factory=lambda: [
            "local_docker_exec_demo_fallback",
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
        default="browser_cli_mvp",
        examples=["browser_cli_mvp"],
    )
    mode_info: CliAccessModeInfo = Field(default_factory=CliAccessModeInfo)
    devices: list[CliAccess]
    message: str




class StudentHint(BaseModel):
    topic: str = Field(..., examples=["Default Gateway"])
    device: str | None = Field(default=None, examples=["r2"])
    level: Literal["general"] = Field(default="general", examples=["general"])
    message: str = Field(
        ...,
        examples=["Check whether the default route points to a reachable next-hop."],
    )


class LabHintsResponse(BaseModel):
    success: bool = True
    session_id: str
    hints: list[StudentHint]
    message: str


class WebCliDeviceReadiness(BaseModel):
    device_id: str = Field(..., examples=["r1"])
    container_name: str | None = Field(default=None, examples=["clab-autonetlab-lab-abc12345-r1"])
    docker_available: bool = Field(default=False)
    container_running: bool = Field(default=False)
    ready: bool = Field(default=False)
    error_code: str | None = Field(default=None)
    message: str


class WebCliReadinessResponse(BaseModel):
    success: bool = True
    session_id: str
    current_mode: CliAccessMode = Field(default="browser_cli_mvp")
    lab_status: SessionStatus
    lab_deployed: bool
    ready: bool
    devices: list[WebCliDeviceReadiness]
    error_code: str | None = Field(default=None)
    message: str
class LabSessionResponse(BaseModel):
    """
    Student-safe lab session response / Ã¶ÄŸrenciye gÃ¼venli lab oturumu yanÄ±tÄ±.

    This response is safe for the student dashboard.
    It intentionally does not include injected_errors, expected fixes,
    solution data, answer data, or internal debug fields.
    """

    success: bool = True
    session_id: str
    student_id: str
    difficulty: Difficulty
    status: SessionStatus
    score: int | None = Field(default=None, examples=[85])
    passed: bool | None = Field(default=None, examples=[False])
    created_at: str | None = Field(default=None, examples=["2026-05-16T13:30:00+00:00"])
    completed_at: str | None = Field(default=None, examples=["2026-05-16T13:45:00+00:00"])
    finished_at: str | None = Field(default=None, examples=["2026-05-16T13:50:00+00:00"])
    topology_summary: dict[str, str | int | list[str]] | None = Field(
        default=None,
        examples=[
            {
                "name": "autonetlab-lab-12345678",
                "node_count": 2,
                "link_count": 1,
                "devices": ["r1", "r2"],
            }
        ],
    )
    scenario: dict | None = Field(
        default=None,
        description=(
            "Student-safe scenario design data such as objective, addressing table, "
            "routing requirements, and expected connectivity. It must not include injected errors."
        ),
    )
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
    Instructor/debug lab session response / eÄŸitmen veya debug lab oturumu yanÄ±tÄ±.

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






class LabSessionListResponse(BaseModel):
    success: bool = True
    sessions: list[LabSessionResponse]
    count: int
    message: str
