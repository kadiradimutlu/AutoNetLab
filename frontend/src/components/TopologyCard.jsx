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
      <p className="muted">{topology.description}</p>

      <h4>Devices / Cihazlar</h4>
      <div className="device-list">
        {topology.devices.map((device) => (
          <div className="list-item" key={device.id}>
            <strong>{device.name}</strong>
            <p className="muted">
              Type: {device.type} | Management IP: {device.managementIp}
            </p>
          </div>
        ))}
      </div>

      <h4>Links / Bağlantılar</h4>
      <div className="link-list">
        {topology.links.map((link, index) => (
          <div className="list-item" key={`${link.source}-${link.target}-${index}`}>
            {link.source} → {link.target}
            <p className="muted">Interface: {link.interface}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

export default TopologyCard;