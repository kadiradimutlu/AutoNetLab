from pathlib import Path
from typing import Any

import yaml
from fastapi import HTTPException, status

from app.schemas.enums import Difficulty
from app.schemas.topology import Topology, TopologyEndpoint, TopologyLink, TopologyNode
from app.services.scenario_catalog import (
    NETWORK_CLIENT_IMAGE,
    SR_BASIC_LINK_SCENARIO_ID,
    SR_LINUX_IMAGE,
    get_scenario,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
TEMPLATES_DIR = PROJECT_ROOT / "containerlab" / "templates"
GENERATED_DIR = PROJECT_ROOT / "containerlab" / "generated"

TEMPLATE_FILE_BY_DIFFICULTY = {
    Difficulty.easy: "easy.clab.yml",
    Difficulty.medium: "medium.clab.yml",
    Difficulty.hard: "hard.clab.yml",
}


def generate_basic_topology(template_name: str = "basic-two-router") -> Topology:
    """
    Backward-compatible Sprint 1 helper.

    This function is kept so older code/tests do not break.
    Sprint 2 uses generate_session_topology() instead.
    """

    return Topology(
        name=template_name,
        nodes=[
            TopologyNode(
                id="r1",
                label="Router 1",
                kind="linux",
                image="alpine:latest",
                mgmt_ipv4=None,
            ),
            TopologyNode(
                id="r2",
                label="Router 2",
                kind="linux",
                image="alpine:latest",
                mgmt_ipv4=None,
            ),
        ],
        links=[
            TopologyLink(
                source=TopologyEndpoint(node="r1", interface="eth1"),
                target=TopologyEndpoint(node="r2", interface="eth1"),
            )
        ],
    )


def generate_session_topology(
    session_id: str,
    difficulty: Difficulty,
    topology_template: str = "basic-two-router",
    scenario_id: str | None = None,
) -> dict[str, Any]:
    """
    Creates a session-specific Containerlab topology file.

    Legacy mode:
    - If scenario_id is omitted, difficulty-based Alpine/Linux templates are used.

    Network realism mode:
    - If scenario_id is provided, the scenario catalog selects a professional topology.
    - Sprint 30 introduces the first Nokia SR Linux scenario.
    """

    _validate_session_id(session_id)

    scenario = get_scenario(scenario_id)

    if scenario is not None:
        if scenario["id"] == SR_BASIC_LINK_SCENARIO_ID:
            return _generate_srl_basic_link_topology(
                session_id=session_id,
                topology_template=scenario["topology_template"],
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported scenario topology: {scenario['id']}",
        )

    template_file = TEMPLATE_FILE_BY_DIFFICULTY.get(difficulty)
    if template_file is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported difficulty: {difficulty}",
        )

    template_path = TEMPLATES_DIR / template_file

    if not template_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Topology template not found: {template_path}",
        )

    data = _load_yaml(template_path)

    lab_name = f"autonetlab-{session_id}"
    data["name"] = lab_name

    output_path = _write_generated_topology(
        session_id=session_id,
        data=data,
    )

    topology = _to_topology_model(data)

    return {
        "topology": topology,
        "topology_file": str(output_path),
        "topology_template": topology_template,
        "lab_name": lab_name,
    }


def _generate_srl_basic_link_topology(
    session_id: str,
    topology_template: str,
) -> dict[str, Any]:
    lab_name = f"autonetlab-{session_id}"

    data: dict[str, Any] = {
        "name": lab_name,
        "topology": {
            "nodes": {
                "srl1": {
                    "kind": "nokia_srlinux",
                    "type": "ixr-d2l",
                    "image": SR_LINUX_IMAGE,
                },
                "client1": {
                    "kind": "linux",
                    "image": NETWORK_CLIENT_IMAGE,
                },
            },
            "links": [
                {
                    "endpoints": [
                        "srl1:e1-1",
                        "client1:eth1",
                    ],
                    "ipv4": [
                        "10.10.10.1/24",
                        "10.10.10.10/24",
                    ],
                }
            ],
        },
    }

    output_path = _write_generated_topology(
        session_id=session_id,
        data=data,
    )

    return {
        "topology": _to_topology_model(data),
        "topology_file": str(output_path),
        "topology_template": topology_template,
        "lab_name": lab_name,
    }


def _write_generated_topology(
    session_id: str,
    data: dict[str, Any],
) -> Path:
    session_dir = GENERATED_DIR / session_id
    _ensure_safe_child_path(session_dir, GENERATED_DIR)

    session_dir.mkdir(parents=True, exist_ok=True)

    output_path = session_dir / "lab.clab.yml"
    output_path.write_text(
        yaml.safe_dump(data, sort_keys=False),
        encoding="utf-8",
    )

    return output_path


def _validate_session_id(session_id: str) -> None:
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")

    if not session_id or any(char not in allowed for char in session_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session_id format.",
        )


def _ensure_safe_child_path(child: Path, parent: Path) -> None:
    child_resolved = child.resolve()
    parent_resolved = parent.resolve()

    try:
        child_resolved.relative_to(parent_resolved)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsafe generated topology path.",
        ) from exc


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Invalid YAML template: {path.name}",
        ) from exc

    if not isinstance(loaded, dict):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Topology template must be a YAML object: {path.name}",
        )

    return loaded


def _to_topology_model(data: dict[str, Any]) -> Topology:
    topology_data = data.get("topology", {})
    nodes_data = topology_data.get("nodes", {})
    links_data = topology_data.get("links", [])

    nodes: list[TopologyNode] = []

    for node_id, node_config in nodes_data.items():
        node_config = node_config or {}

        nodes.append(
            TopologyNode(
                id=node_id,
                label=_make_node_label(node_id=node_id, kind=node_config.get("kind")),
                kind=node_config.get("kind", "linux"),
                image=node_config.get("image"),
                mgmt_ipv4=node_config.get("mgmt_ipv4"),
            )
        )

    links: list[TopologyLink] = []

    for link in links_data:
        endpoints = link.get("endpoints", [])

        if len(endpoints) != 2:
            continue

        source = _parse_endpoint(endpoints[0])
        target = _parse_endpoint(endpoints[1])

        links.append(
            TopologyLink(
                source=source,
                target=target,
            )
        )

    return Topology(
        name=data.get("name", "autonetlab"),
        nodes=nodes,
        links=links,
    )


def _parse_endpoint(raw_endpoint: str) -> TopologyEndpoint:
    node, interface = raw_endpoint.split(":", maxsplit=1)

    return TopologyEndpoint(
        node=node,
        interface=interface,
    )


def _make_node_label(node_id: str, kind: str | None = None) -> str:
    if kind == "nokia_srlinux":
        suffix = node_id.replace("srl", "")
        return f"SR Linux Router {suffix}" if suffix.isdigit() else "SR Linux Router"

    if node_id.startswith("client") and node_id.replace("client", "").isdigit():
        return f"Client {node_id.replace('client', '')}"

    if node_id.startswith("r") and node_id[1:].isdigit():
        return f"Router {node_id[1:]}"

    return node_id.upper()
