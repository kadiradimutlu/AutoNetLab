function StatCard({ title, value, helper }) {
  return (
    <section className="card">
      <h3>{title}</h3>
      <div className="stat-value">{value}</div>
      <p className="muted">{helper}</p>
    </section>
  );
}

export default StatCard;