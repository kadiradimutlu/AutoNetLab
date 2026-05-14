import { useLanguage } from "../hooks/useLanguage";

function TopologyCard({ topology }) {
  const { t } = useLanguage();

  if (!topology) {
    return (
      <section className="card">
        <h3>{t("topology")}</h3>
        <p className="muted">{t("topologyLoading")}</p>
      </section>
    );
  }

  return (
    <section className="card">
      <h3>{t("topology")}</h3>

      <div className="info-row">
        <span>{t("topologyName")}</span>
        <strong>{topology.name}</strong>
      </div>

      <h4>{t("nodes")}</h4>
      <div className="device-list">
        {topology.nodes.map((node) => (
          <div className="list-item" key={node.id}>
            <strong>{node.label}</strong>
            <p className="muted">
              {t("id")}: {node.id} | {t("kind")}: {node.kind} | {t("image")}:{" "}
              {node.image || "-"}
            </p>
            <p className="muted">
              {t("managementIpv4")}: {node.mgmt_ipv4 || t("notAssignedYet")}
            </p>
          </div>
        ))}
      </div>

      <h4>{t("links")}</h4>
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