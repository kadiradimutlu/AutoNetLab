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
  return {
    id: node.id || node.name || `node-${index + 1}`,
    label: node.label || node.name || node.id || `Node ${index + 1}`,
    kind: node.kind || node.type || "network-device",
    image: node.image || "-",
    managementIp:
      node.mgmt_ipv4 ||
      node.managementIp ||
      node.management_ip ||
      null
  };
}

function normalizeLink(link, index) {
  const sourceNode =
    link?.source?.node ||
    link?.source ||
    link?.from ||
    `source-${index + 1}`;

  const sourceInterface =
    link?.source?.interface ||
    link?.source_interface ||
    link?.interface ||
    "-";

  const targetNode =
    link?.target?.node ||
    link?.target ||
    link?.to ||
    `target-${index + 1}`;

  const targetInterface =
    link?.target?.interface ||
    link?.target_interface ||
    link?.interface ||
    "-";

  return {
    sourceNode,
    sourceInterface,
    targetNode,
    targetInterface
  };
}

function getNodeInitial(node) {
  return String(node.label || node.id || "?").charAt(0).toUpperCase();
}

function TopologyCard({ topology, difficulty, status }) {
  if (!topology) {
    return (
      <section className="card topology-card">
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

  return (
    <section className="card topology-card">
      <div className="section-title-row">
        <div>
          <h3>Topology Visualization</h3>
          <p className="muted">
            A student-safe overview of the generated network topology.
          </p>
        </div>

        {difficulty && (
          <span className={`badge ${String(difficulty).toLowerCase()}`}>
            {difficulty}
          </span>
        )}
      </div>

      <div className="topology-summary-row">
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

      <div className="topology-map-panel">
        <div className="topology-node-grid">
          {nodes.length === 0 && (
            <p className="muted">No topology devices were found.</p>
          )}

          {nodes.map((node) => (
            <div className="topology-node-card" key={node.id}>
              <div className="topology-node-icon">{getNodeInitial(node)}</div>

              <div>
                <strong>{node.label}</strong>
                <p className="muted">
                  {node.id} · {node.kind}
                </p>
              </div>
            </div>
          ))}
        </div>

        {links.length > 0 && (
          <div className="topology-link-strip">
            {links.map((link, index) => (
              <div
                className="topology-link-pill"
                key={`${link.sourceNode}-${link.targetNode}-${index}`}
              >
                <span>
                  {link.sourceNode}:{link.sourceInterface}
                </span>
                <strong>→</strong>
                <span>
                  {link.targetNode}:{link.targetInterface}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      <h4>Devices</h4>
      <div className="device-list">
        {nodes.length === 0 && (
          <p className="muted">No devices are available yet.</p>
        )}

        {nodes.map((node) => (
          <div className="list-item" key={node.id}>
            <div className="result-title-row">
              <strong>{node.label}</strong>
              <span className="badge">{node.kind}</span>
            </div>

            <div className="device-detail-grid">
              <div>
                <span>ID</span>
                <strong>{node.id}</strong>
              </div>

              <div>
                <span>Image</span>
                <strong>{node.image}</strong>
              </div>

              <div>
                <span>Management IPv4</span>
                <strong>{node.managementIp || "Not assigned yet"}</strong>
              </div>
            </div>
          </div>
        ))}
      </div>

      <h4>Links</h4>
      <div className="link-list">
        {links.length === 0 && (
          <p className="muted">No links are available yet.</p>
        )}

        {links.map((link, index) => (
          <div
            className="list-item"
            key={`${link.sourceNode}-${link.targetNode}-${index}`}
          >
            <div className="link-path-row">
              <strong>
                {link.sourceNode}:{link.sourceInterface}
              </strong>
              <span>connected to</span>
              <strong>
                {link.targetNode}:{link.targetInterface}
              </strong>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

export default TopologyCard;