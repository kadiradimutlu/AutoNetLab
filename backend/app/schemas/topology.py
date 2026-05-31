from pydantic import BaseModel, Field


class TopologyNode(BaseModel):
    id: str = Field(..., examples=["r1"])
    label: str = Field(..., examples=["Router 1"])
    kind: str = Field(..., examples=["linux"])
    image: str | None = Field(default=None, examples=["alpine:latest"])
    mgmt_ipv4: str | None = Field(default=None, examples=["172.20.20.11"])
    role: str | None = Field(default=None, examples=["router"])


class TopologyEndpoint(BaseModel):
    node: str = Field(..., examples=["r1"])
    interface: str = Field(..., examples=["eth1"])


class TopologyLink(BaseModel):
    source: TopologyEndpoint
    target: TopologyEndpoint


class Topology(BaseModel):
    name: str = Field(..., examples=["srl-edge-link"])
    nodes: list[TopologyNode]
    links: list[TopologyLink]