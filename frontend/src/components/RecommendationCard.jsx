function RecommendationCard({ recommendations = [] }) {
  if (!recommendations.length) {
    return (
      <section className="card">
        <h3>Recommendation / Öneri</h3>
        <p className="muted">
          Recommendations will appear after validation if any topic needs review.
        </p>
      </section>
    );
  }

  return (
    <section className="card">
      <h3>Recommendation / Öneri</h3>

      <div className="recommendation-list">
        {recommendations.map((message, index) => (
          <div className="list-item" key={`${message}-${index}`}>
            <strong>Recommendation {index + 1}</strong>
            <p>{message}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

export default RecommendationCard;