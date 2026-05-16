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

function getDeviceIconLabel(node) {
  const kind = String(node.kind || "").toLowerCase();

  if (kind.includes("router") || node.id.startsWith("r")) {
    return "R";
  }

  if (kind.includes("switch") || node.id.startsWith("s")) {
    return "S";
  }

  return "D";
}

function getReadableKind(kind) {
  const normalizedKind = String(kind || "network-device").replace(/_/g, " ");

  return normalizedKind.charAt(0).toUpperCase() + normalizedKind.slice(1);
}

function TopologyNode({ node, cliInfo }) {
  const hasCliAccess = Boolean(cliInfo);
  const containerName = cliInfo?.containerName || cliInfo?.container_name || "-";

  return (
    <article className="network-node-card">
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
            <span>Management IP</span>
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
        <strong>{primaryLink.sourceInterface}</strong>
        <span>↔</span>
        <strong>{primaryLink.targetInterface}</strong>
      </div>
    </div>
  );
}

function TopologyLegend() {
  const items = [
    {
      marker: "R",
      label: "Router / Device"
    },
    {
      marker: "━",
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

  return (
    <section className={`card topology-card topology-card-polished ${variant === "workspace" ? "topology-card-workspace" : ""}`}>
      <div className="section-title-row">
        <div>
          <h3>Network Topology</h3>
          <p className="muted">
            Cisco-like student-safe diagram of the generated Containerlab topology.
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
            <strong>{nodes.length} devices · {links.length} links</strong>
          </div>

          <div className={`network-diagram-canvas ${isSimplePair ? "pair" : "multi"}`}>
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
            ) : (
              nodes.map((node) => (
                <TopologyNode
                  node={node}
                  cliInfo={findCliAccessForNode(node, cliAccess)}
                  key={node.id}
                />
              ))
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
              Link metadata is generated by backend topology contracts and does not expose solution details.
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

              <span className="topology-link-arrow">↔</span>

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
