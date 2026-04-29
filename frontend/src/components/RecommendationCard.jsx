function RecommendationCard({ recommendation }) {
  if (!recommendation) {
    return (
      <section className="card">
        <h3>Recommendation / Öneri</h3>
        <p className="muted">Recommendation data is loading...</p>
      </section>
    );
  }

  return (
    <section className="card">
      <h3>Recommendation / Öneri</h3>

      <div className="recommendation-list">
        {recommendation.recommendations.map((item) => (
          <div className="list-item" key={item.id}>
            <strong>{item.topic}</strong>
            <p>{item.message}</p>
            <p className="muted">Priority: {item.priority}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

export default RecommendationCard;