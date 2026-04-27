from app.schemas.topology import Topology, TopologyEndpoint, TopologyLink, TopologyNode


def generate_basic_topology(template_name: str = "basic-two-router") -> Topology:
    """
    Sprint 1 MVP topology generator.

    For now, this function returns a fixed two-node topology.
    Later, it can generate different YAML topologies based on difficulty.
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