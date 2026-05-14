import AnalyticsEmptyState from "./AnalyticsEmptyState";

function getFailureWidth(value) {
  return `${Math.min(Math.max(Number(value) || 0, 0), 100)}%`;
}

function normalizeSeverity(severity) {
  return severity || "low";
}

function TopicWeaknessList({ topicWeaknesses }) {
  const items = Array.isArray(topicWeaknesses) ? topicWeaknesses : [];

  return (
    <section className="card analytics-card">
      <div className="section-title-row">
        <div>
          <h3>Topic Weakness Analytics</h3>
          <p className="muted">
            Topics where students fail most often during validation.
          </p>
        </div>
      </div>

      {items.length === 0 ? (
        <AnalyticsEmptyState
          title="No topic weakness data yet."
          message="Topic weakness analytics will appear after completed validation attempts."
        />
      ) : (
        <div className="topic-weakness-list">
          {items.map((item) => (
            <div className="topic-weakness-card" key={item.topic}>
              <div className="topic-weakness-header">
                <div>
                  <strong>{item.label || item.topic}</strong>
                  <p className="muted">
                    {item.fail_count} failed checks out of {item.attempt_count} attempts
                  </p>
                </div>

                <span className={`badge ${normalizeSeverity(item.severity)}`}>
                  {normalizeSeverity(item.severity)}
                </span>
              </div>

              <div className="analytics-bar-track">
                <div
                  className="analytics-bar-fill danger"
                  style={{
                    "--bar-width": getFailureWidth(item.failure_rate)
                  }}
                />
              </div>

              <div className="analytics-bar-meta">
                <span>Failure Rate: {Number(item.failure_rate || 0).toFixed(1)}%</span>
                <span>Average Score: {Number(item.average_score || 0).toFixed(1)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

export default TopicWeaknessList;