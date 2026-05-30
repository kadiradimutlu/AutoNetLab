
const LINK_ARROW = "\u2194";
const LINK_MARKER = "\u2501";
const DEVICE_COUNT_SEPARATOR = "\u00b7";

function getNodeList(topology) {
  if (Array.isArray(topology?.nodes)) {
    return topology.nodes;
  }

  if (Array.isArray(topology?.devices)) {
    return topology.devices;
  }

  return [];
}

function getLinkList(topology) {
  if (Array.isArray(topology?.links)) {
    return topology.links;
  }

  return [];
}

function normalizeNode(node, index) {
  const safeNode = node && typeof node === "object" ? node : {};

  return {
    id: safeNode.id || safeNode.name || `node-${index + 1}`,
    label: safeNode.label || safeNode.name || safeNode.id || `Node ${index + 1}`,
    kind: safeNode.kind || safeNode.type || "network-device",
    image: safeNode.image || "-",
    managementIp:
      safeNode.mgmt_ipv4 ||
      safeNode.managementIp ||
      safeNode.management_ip ||
      null
  };
}

function normalizeLink(link, index) {
  const safeLink = link && typeof link === "object" ? link : {};

  const sourceNode =
    safeLink?.source?.node ||
    safeLink?.source ||
    safeLink?.from ||
    `source-${index + 1}`;

  const sourceInterface =
    safeLink?.source?.interface ||
    safeLink?.source_interface ||
    safeLink?.interface ||
    "-";

  const targetNode =
    safeLink?.target?.node ||
    safeLink?.target ||
    safeLink?.to ||
    `target-${index + 1}`;

  const targetInterface =
    safeLink?.target?.interface ||
    safeLink?.target_interface ||
    safeLink?.interface ||
    "-";

  return {
    sourceNode,
    sourceInterface,
    targetNode,
    targetInterface
  };
}

function getSafeText(value, fallback = "-") {
  if (value === undefined || value === null || value === "") {
    return fallback;
  }

  return String(value);
}

function getCliDeviceId(cli, index) {
  return (
    cli.deviceId ||
    cli.device_id ||
    cli.device ||
    cli.deviceName ||
    cli.device_name ||
    cli.name ||
    `device-${index + 1}`
  );
}

function findCliAccessForNode(node, cliAccess = []) {
  return cliAccess.find((cli, index) => {
    const cliDeviceId = getCliDeviceId(cli, index);

    return cliDeviceId === node.id || cliDeviceId === node.label;
  });
}

function getNodeCategory(node) {
  const kind = String(node.kind || "").toLowerCase();
  const id = String(node.id || "").toLowerCase();
  const label = String(node.label || "").toLowerCase();

  if (kind.includes("srl") || kind.includes("router") || label.includes("router") || id.startsWith("r")) {
    return "router";
  }

  if (kind.includes("linux") || kind.includes("client") || label.includes("client") || id.includes("client")) {
    return "client";
  }

  if (kind.includes("switch") || id.startsWith("s")) {
    return "switch";
  }

  return "device";
}

function getDeviceIconLabel(node) {
  const category = getNodeCategory(node);
  const kind = String(node.kind || "").toLowerCase();

  if (kind.includes("srl")) {
    return "SR";
  }

  if (category === "router") {
    return "R";
  }

  if (category === "switch") {
    return "S";
  }

  if (category === "client") {
    return "C";
  }

  return "D";
}

function getReadableKind(kind) {
  const normalizedKind = String(kind || "network-device").toLowerCase();

  if (normalizedKind.includes("srl")) {
    return "Nokia SR Linux";
  }

  if (normalizedKind === "linux") {
    return "Linux Client";
  }

  const readableKind = normalizedKind.replace(/_/g, " ");

  return readableKind.charAt(0).toUpperCase() + readableKind.slice(1);
}

function getNodeCardClass(node) {
  const category = getNodeCategory(node);

  if (String(node.kind || "").toLowerCase().includes("srl")) {
    return "topology-node-srlinux";
  }

  if (category === "client") {
    return "topology-node-linux";
  }

  if (category === "router") {
    return "topology-node-router";
  }

  return "topology-node-generic";
}

function normalizeTopologyKey(value) {
  return String(value || "").trim().toLowerCase();
}

function buildRingPositionMap(nodes) {
  return nodes.reduce((positionMap, node, index) => {
    positionMap.set(normalizeTopologyKey(node.id), index);
    positionMap.set(normalizeTopologyKey(node.label), index);
    return positionMap;
  }, new Map());
}

function getRingEdgeClass(link, positionMap, index) {
  const sourceIndex = positionMap.get(normalizeTopologyKey(link.sourceNode));
  const targetIndex = positionMap.get(normalizeTopologyKey(link.targetNode));

  if (sourceIndex === undefined || targetIndex === undefined) {
    return index % 2 === 0 ? "diagonal-a" : "diagonal-b";
  }

  const pairKey = [sourceIndex, targetIndex].sort((left, right) => left - right).join("-");

  if (pairKey === "0-1") {
    return "top";
  }

  if (pairKey === "1-2") {
    return "right";
  }

  if (pairKey === "2-3") {
    return "bottom";
  }

  if (pairKey === "0-3") {
    return "left";
  }

  return index % 2 === 0 ? "diagonal-a" : "diagonal-b";
}

function getRingLineCoordinates(edgeClass) {
  const coordinatesByEdge = {
    top: {
      x1: 36,
      y1: 20,
      x2: 64,
      y2: 20
    },
    right: {
      x1: 78,
      y1: 30,
      x2: 78,
      y2: 70
    },
    bottom: {
      x1: 64,
      y1: 80,
      x2: 36,
      y2: 80
    },
    left: {
      x1: 22,
      y1: 70,
      x2: 22,
      y2: 30
    },
    "diagonal-a": {
      x1: 36,
      y1: 25,
      x2: 64,
      y2: 75
    },
    "diagonal-b": {
      x1: 64,
      y1: 25,
      x2: 36,
      y2: 75
    }
  };

  return coordinatesByEdge[edgeClass] || coordinatesByEdge["diagonal-a"];
}

function getRingNodeClass(index) {
  return `network-ring-node-${index + 1}`;
}

function getRingLinkLabel(link) {
  return `${getSafeText(link.sourceNode)}:${getSafeText(link.sourceInterface)} ${LINK_ARROW} ${getSafeText(link.targetNode)}:${getSafeText(link.targetInterface)}`;
}

function TopologyNode({ node, cliInfo }) {
  const hasCliAccess = Boolean(cliInfo);
  const containerName = cliInfo?.containerName || cliInfo?.container_name || "-";

  return (
    <article className={`network-node-card ${getNodeCardClass(node)}`}>
      <div className="network-device-shell">
        <div className="network-device-icon">
          <span>{getDeviceIconLabel(node)}</span>
        </div>

        <div className="network-device-led-row" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
      </div>

      <div className="network-node-content">
        <div className="network-node-title-row">
          <div>
            <strong>{node.label}</strong>
            <p>{node.id}</p>
          </div>

          <span className={`badge ${hasCliAccess ? "pass" : "neutral"}`}>
            {hasCliAccess ? "CLI" : "Device"}
          </span>
        </div>

        <div className="network-node-detail-grid">
          <div>
            <span>Kind</span>
            <strong>{getReadableKind(node.kind)}</strong>
          </div>

          <div>
            <span>Image</span>
            <strong>{getSafeText(node.image)}</strong>
          </div>

          <div>
            <span>Mgmt IP</span>
            <strong>{getSafeText(node.managementIp, "Not assigned")}</strong>
          </div>

          <div>
            <span>Container</span>
            <strong>{containerName}</strong>
          </div>
        </div>
      </div>
    </article>
  );
}

function TopologyLinkBridge({ links }) {
  const primaryLink = links[0];

  if (!primaryLink) {
    return (
      <div className="network-link-bridge empty">
        <span>No link metadata</span>
      </div>
    );
  }

  return (
    <div className="network-link-bridge">
      <div className="network-link-line" />

      <div className="network-link-label">
        <strong>{primaryLink.sourceNode} {primaryLink.sourceInterface}</strong>
        <span>{LINK_ARROW}</span>
        <strong>{primaryLink.targetNode} {primaryLink.targetInterface}</strong>
      </div>
    </div>
  );
}


function getTopologyNodeKeys(node) {
  return [
    normalizeTopologyKey(node.id),
    normalizeTopologyKey(node.label)
  ].filter(Boolean);
}

function linkMatchesNodePair(link, leftNode, rightNode) {
  const leftNodeKeys = getTopologyNodeKeys(leftNode);
  const rightNodeKeys = getTopologyNodeKeys(rightNode);
  const sourceKey = normalizeTopologyKey(link.sourceNode);
  const targetKey = normalizeTopologyKey(link.targetNode);

  return (
    (leftNodeKeys.includes(sourceKey) && rightNodeKeys.includes(targetKey)) ||
    (leftNodeKeys.includes(targetKey) && rightNodeKeys.includes(sourceKey))
  );
}

function findLinkBetweenNodes(links, leftNode, rightNode) {
  return links.find((link) => linkMatchesNodePair(link, leftNode, rightNode)) || null;
}

function getInlineLinkTitle(link, leftNode, rightNode) {
  if (!link) {
    return `${getSafeText(leftNode?.id)} ${LINK_ARROW} ${getSafeText(rightNode?.id)}`;
  }

  return `${getSafeText(link.sourceNode)}:${getSafeText(link.sourceInterface)} ${LINK_ARROW} ${getSafeText(link.targetNode)}:${getSafeText(link.targetInterface)}`;
}

function TopologyInlineLink({ link, leftNode, rightNode }) {
  const title = getInlineLinkTitle(link, leftNode, rightNode);

  return (
    <div className={`network-link-bridge topology-linear-link ${link ? "" : "empty"}`} title={title}>
      <div className="network-link-line" />

      <div className="network-link-label">
        {link ? (
          <>
            <strong>{link.sourceNode} {link.sourceInterface}</strong>
            <span>{LINK_ARROW}</span>
            <strong>{link.targetNode} {link.targetInterface}</strong>
          </>
        ) : (
          <span>No link metadata</span>
        )}
      </div>
    </div>
  );
}

function LinearTopologyDiagram({ nodes, links, cliAccess }) {
  const diagramItems = [];

  nodes.forEach((node, index) => {
    const nextNode = nodes[index + 1];

    diagramItems.push(
      <div className="topology-linear-node" key={`node-${node.id}`}>
        <TopologyNode
          node={node}
          cliInfo={findCliAccessForNode(node, cliAccess)}
        />
      </div>
    );

    if (nextNode) {
      const link = findLinkBetweenNodes(links, node, nextNode);

      diagramItems.push(
        <TopologyInlineLink
          key={`link-${node.id}-${nextNode.id}-${index}`}
          link={link}
          leftNode={node}
          rightNode={nextNode}
        />
      );
    }
  });

  return (
    <div className="topology-linear-diagram" aria-label="Multi-device linear topology diagram">
      {diagramItems}
    </div>
  );
}

function RingTopologyDiagram({ nodes, links, cliAccess }) {
  const positionMap = buildRingPositionMap(nodes);
  const ringLinks = links.map((link, index) => {
    const edgeClass = getRingEdgeClass(link, positionMap, index);
    const coordinates = getRingLineCoordinates(edgeClass);

    return {
      link,
      edgeClass,
      coordinates
    };
  });

  return (
    <div className="network-ring-diagram" aria-label="Four-device ring topology diagram">
      <svg
        className="network-ring-svg"
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        {ringLinks.map(({ link, edgeClass, coordinates }, index) => (
          <g key={`${link.sourceNode}-${link.targetNode}-${index}`}>
            <line
              className={`network-ring-line ${edgeClass}`}
              x1={coordinates.x1}
              y1={coordinates.y1}
              x2={coordinates.x2}
              y2={coordinates.y2}
            />
            <circle
              className="network-ring-endpoint"
              cx={coordinates.x1}
              cy={coordinates.y1}
              r="1.4"
            />
            <circle
              className="network-ring-endpoint"
              cx={coordinates.x2}
              cy={coordinates.y2}
              r="1.4"
            />
          </g>
        ))}
      </svg>

      <div className="network-ring-link-label-layer" aria-hidden="true">
        {ringLinks.map(({ link, edgeClass }, index) => (
          <span
            className={`network-ring-link-label ${edgeClass}`}
            key={`${link.sourceNode}-${link.targetNode}-${index}`}
            title={getRingLinkLabel(link)}
          >
            {getRingLinkLabel(link)}
          </span>
        ))}
      </div>

      <div className="network-ring-node-layer">
        {nodes.map((node, index) => (
          <div
            className={`network-ring-node ${getRingNodeClass(index)}`}
            key={node.id}
          >
            <TopologyNode
              node={node}
              cliInfo={findCliAccessForNode(node, cliAccess)}
            />
          </div>
        ))}
      </div>
    </div>
  );
}


const CAMPUS_NODE_ORDER = ["client1", "srl1", "srl3", "srl2", "client2", "srl4"];

const CAMPUS_EDGE_CLASSES = {
  "client1-srl1": "client1-srl1",
  "srl1-client1": "client1-srl1",
  "srl1-srl3": "srl1-srl3",
  "srl3-srl1": "srl1-srl3",
  "srl3-srl2": "srl3-srl2",
  "srl2-srl3": "srl3-srl2",
  "srl2-client2": "srl2-client2",
  "client2-srl2": "srl2-client2",
  "srl1-srl4": "srl1-srl4",
  "srl4-srl1": "srl1-srl4",
  "srl4-srl2": "srl4-srl2",
  "srl2-srl4": "srl4-srl2"
};

function getCampusNodeSet(nodes) {
  return new Set(nodes.map((node) => normalizeTopologyKey(node.id)));
}

function isCampusTopology(topology, nodes, links) {
  const topologyName = normalizeTopologyKey(topology?.name || topology?.id || topology?.scenario_id || "");
  const nodeSet = getCampusNodeSet(nodes);
  const hasCampusNodes = CAMPUS_NODE_ORDER.every((nodeId) => nodeSet.has(nodeId));
  const hasCampusName = topologyName.includes("campus-core-static-routing") || topologyName.includes("campus");

  return hasCampusNodes && (hasCampusName || links.length >= 5);
}

function orderCampusNodes(nodes) {
  const nodeMap = nodes.reduce((result, node) => {
    result.set(normalizeTopologyKey(node.id), node);
    return result;
  }, new Map());

  const orderedNodes = CAMPUS_NODE_ORDER
    .map((nodeId) => nodeMap.get(nodeId))
    .filter(Boolean);
  const orderedNodeIds = new Set(orderedNodes.map((node) => normalizeTopologyKey(node.id)));
  const remainingNodes = nodes.filter((node) => !orderedNodeIds.has(normalizeTopologyKey(node.id)));

  return [...orderedNodes, ...remainingNodes];
}

function getCampusEdgeClass(link, index) {
  const sourceKey = normalizeTopologyKey(link.sourceNode);
  const targetKey = normalizeTopologyKey(link.targetNode);
  const pairKey = `${sourceKey}-${targetKey}`;

  return CAMPUS_EDGE_CLASSES[pairKey] || `extra-${index}`;
}

function getCampusLineCoordinates(edgeClass) {
  const coordinatesByEdge = {
    "client1-srl1": { x1: 16, y1: 18, x2: 24, y2: 18 },
    "srl1-srl3": { x1: 34, y1: 18, x2: 44, y2: 18 },
    "srl3-srl2": { x1: 54, y1: 18, x2: 64, y2: 18 },
    "srl2-client2": { x1: 74, y1: 18, x2: 82, y2: 18 },
    "srl1-srl4": { x1: 30, y1: 26, x2: 45, y2: 42 },
    "srl4-srl2": { x1: 55, y1: 42, x2: 70, y2: 26 }
  };

  return coordinatesByEdge[edgeClass] || { x1: 48, y1: 30, x2: 52, y2: 30 };
}

function getCampusLinkLabel(link) {
  return `${getSafeText(link.sourceNode)} ${getSafeText(link.sourceInterface)} ${LINK_ARROW} ${getSafeText(link.targetNode)} ${getSafeText(link.targetInterface)}`;
}

function CampusTopologyDiagram({ nodes, links, cliAccess }) {
  const campusNodes = orderCampusNodes(nodes);
  const campusLinks = links.map((link, index) => {
    const edgeClass = getCampusEdgeClass(link, index);

    return {
      link,
      edgeClass,
      coordinates: getCampusLineCoordinates(edgeClass)
    };
  });

  return (
    <div className="campus-topology-diagram" aria-label="Campus core static routing topology diagram">
      <svg
        className="campus-topology-svg"
        viewBox="0 0 100 58"
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        {campusLinks.map(({ link, edgeClass, coordinates }, index) => (
          <g key={`${link.sourceNode}-${link.targetNode}-${index}`}>
            <line
              className={`campus-topology-line campus-link-line-${edgeClass}`}
              x1={coordinates.x1}
              y1={coordinates.y1}
              x2={coordinates.x2}
              y2={coordinates.y2}
            />
            <circle className="campus-topology-endpoint" cx={coordinates.x1} cy={coordinates.y1} r="1.1" />
            <circle className="campus-topology-endpoint" cx={coordinates.x2} cy={coordinates.y2} r="1.1" />
          </g>
        ))}
      </svg>

      <div className="campus-link-label-layer" aria-hidden="true">
        {campusLinks.map(({ link, edgeClass }, index) => (
          <span
            className={`campus-link-label campus-link-label-${edgeClass}`}
            key={`${link.sourceNode}-${link.targetNode}-label-${index}`}
            title={getCampusLinkLabel(link)}
          >
            {getCampusLinkLabel(link)}
          </span>
        ))}
      </div>

      <div className="campus-node-layer">
        {campusNodes.map((node) => (
          <div className={`campus-node campus-node-${normalizeTopologyKey(node.id)}`} key={node.id}>
            <TopologyNode
              node={node}
              cliInfo={findCliAccessForNode(node, cliAccess)}
            />
          </div>
        ))}
      </div>
    </div>
  );
}

function TopologyLegend() {
  const items = [
    {
      marker: "SR",
      label: "SR Linux Router"
    },
    {
      marker: "C",
      label: "Linux Client"
    },
    {
      marker: LINK_MARKER,
      label: "Network Link"
    },
    {
      marker: "eth",
      label: "Interface"
    },
    {
      marker: "CLI",
      label: "CLI Available"
    }
  ];

  return (
    <div className="topology-legend">
      {items.map((item) => (
        <div className="topology-legend-item" key={item.label}>
          <span>{item.marker}</span>
          <strong>{item.label}</strong>
        </div>
      ))}
    </div>
  );
}

function TopologyCard({
  topology,
  difficulty,
  status,
  cliAccess = [],
  variant = "default",
  actions = null
}) {
  if (!topology) {
    return (
      <section className={`card topology-card topology-card-polished ${variant === "workspace" ? "topology-card-workspace" : ""}`}>
        <h3>Topology</h3>
        <p className="muted">Topology information is loading.</p>
      </section>
    );
  }

  const nodes = getNodeList(topology).map((node, index) =>
    normalizeNode(node, index)
  );
  const links = getLinkList(topology).map((link, index) =>
    normalizeLink(link, index)
  );

  const hasNodes = nodes.length > 0;
  const isSimplePair = nodes.length === 2;
  const isFourNodeRing = nodes.length === 4 && links.length >= 4;
  const isCampusTopologyDiagram = isCampusTopology(topology, nodes, links);
  const isLinearMultiNode = nodes.length > 2 && !isFourNodeRing && !isCampusTopologyDiagram;

  return (
    <section className={`card topology-card topology-card-polished ${variant === "workspace" ? "topology-card-workspace" : ""}`}>
      <div className="section-title-row">
        <div>
          <h3>Network Topology</h3>
          <p className="muted">
            Topology diagram of the generated Containerlab lab.
          </p>
        </div>

        <div className="topology-title-action-row">
          {difficulty && (
            <span className={`badge ${String(difficulty).toLowerCase()}`}>
              {difficulty}
            </span>
          )}

          {actions}
        </div>
      </div>

      <div className="topology-summary-row topology-summary-polished">
        <div>
          <span className="muted">Topology Name</span>
          <strong>{topology.name || "Unnamed topology"}</strong>
        </div>

        <div>
          <span className="muted">Devices</span>
          <strong>{nodes.length}</strong>
        </div>

        <div>
          <span className="muted">Links</span>
          <strong>{links.length}</strong>
        </div>

        <div>
          <span className="muted">Status</span>
          <strong>{status || "-"}</strong>
        </div>
      </div>

      {!hasNodes && (
        <div className="topology-empty-state">
          <strong>No topology devices found.</strong>
          <p>
            Create a lab session or refresh the session details to load topology metadata.
          </p>
        </div>
      )}

      {hasNodes && (
        <div className="network-diagram-shell">
          <div className="network-diagram-toolbar">
            <span>Generated Lab Diagram</span>
            <strong>
              {nodes.length} devices {DEVICE_COUNT_SEPARATOR} {links.length} links
            </strong>
          </div>

          <div className={`network-diagram-canvas ${isSimplePair ? "pair" : "multi"} ${isFourNodeRing ? "ring" : ""} ${isCampusTopologyDiagram ? "campus" : ""} ${isLinearMultiNode ? "linear" : ""}`}>
            {isSimplePair ? (
              <>
                <TopologyNode
                  node={nodes[0]}
                  cliInfo={findCliAccessForNode(nodes[0], cliAccess)}
                />

                <TopologyLinkBridge links={links} />

                <TopologyNode
                  node={nodes[1]}
                  cliInfo={findCliAccessForNode(nodes[1], cliAccess)}
                />
              </>
            ) : isFourNodeRing ? (
              <RingTopologyDiagram
                nodes={nodes}
                links={links}
                cliAccess={cliAccess}
              />
            ) : isCampusTopologyDiagram ? (
              <CampusTopologyDiagram
                nodes={nodes}
                links={links}
                cliAccess={cliAccess}
              />
            ) : (
              <LinearTopologyDiagram
                nodes={nodes}
                links={links}
                cliAccess={cliAccess}
              />
            )}
          </div>

          <TopologyLegend />
        </div>
      )}

      <div className="topology-detail-section">
        <div className="section-title-row compact">
          <div>
            <h4>Interface Links</h4>
            <p className="muted">
              Link metadata is generated by topology contracts and does not expose solution details.
            </p>
          </div>

          <span className="badge neutral">{links.length} links</span>
        </div>

        <div className="topology-link-list-polished">
          {links.length === 0 && (
            <div className="topology-empty-state compact">
              <strong>No links available.</strong>
              <p>The topology response does not include link metadata yet.</p>
            </div>
          )}

          {links.map((link, index) => (
            <div
              className="topology-link-card-polished"
              key={`${link.sourceNode}-${link.targetNode}-${index}`}
            >
              <div>
                <span>Source</span>
                <strong>{link.sourceNode}</strong>
                <small>{link.sourceInterface}</small>
              </div>

              <span className="topology-link-arrow">{LINK_ARROW}</span>

              <div>
                <span>Target</span>
                <strong>{link.targetNode}</strong>
                <small>{link.targetInterface}</small>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export default TopologyCard;

