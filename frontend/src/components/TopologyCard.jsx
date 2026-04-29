function TopologyCard({ topology }) {
  if (!topology) {
    return (
      <section className="card">
        <h3>Topology / Topoloji</h3>
        <p className="muted">Topology data is loading...</p>
      </section>
    );
  }

  return (
    <section className="card">
      <h3>Topology / Topoloji</h3>

      <div className="info-row">
        <span>Topology Name</span>
        <strong>{topology.name}</strong>
      </div>

      <h4>Nodes / Düğümler</h4>
      <div className="device-list">
        {topology.nodes.map((node) => (
          <div className="list-item" key={node.id}>
            <strong>{node.label}</strong>
            <p className="muted">
              ID: {node.id} | Kind: {node.kind} | Image: {node.image || "-"}
            </p>
            <p className="muted">
              Management IPv4: {node.mgmt_ipv4 || "Not assigned yet"}
            </p>
          </div>
        ))}
      </div>

      <h4>Links / Bağlantılar</h4>
      <div className="link-list">
        {topology.links.map((link, index) => (
          <div
            className="list-item"
            key={`${link.source.node}-${link.target.node}-${index}`}
          >
            <strong>
              {link.source.node}:{link.source.interface} → {link.target.node}:
              {link.target.interface}
            </strong>
          </div>
        ))}
      </div>
    </section>
  );
}

export default TopologyCard;