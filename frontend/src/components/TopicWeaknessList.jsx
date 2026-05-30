import AnalyticsEmptyState from "./AnalyticsEmptyState";

function getFailureWidth(value) {
  return `${Math.min(Math.max(Number(value) || 0, 0), 100)}%`;
}

function normalizeSeverity(severity) {
  const normalizedSeverity = String(severity || "low").toLowerCase();

  if (["high", "medium", "low"].includes(normalizedSeverity)) {
    return normalizedSeverity;
  }

  return "low";
}

function formatNumber(value, fallback = "0") {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }

  const numericValue = Number(value);

  if (Number.isNaN(numericValue)) {
    return fallback;
  }

  return numericValue.toLocaleString("en-US", {
    maximumFractionDigits: 2
  });
}

function hasWeaknessSignal(item) {
  const failCount = Number(item?.fail_count ?? item?.failed_count ?? item?.failures ?? 0);
  const failureRate = Number(item?.failure_rate ?? item?.fail_rate ?? 0);

  return failCount > 0 || failureRate > 0;
}

function TopicWeaknessList({ topicWeaknesses }) {
  const items = Array.isArray(topicWeaknesses)
    ? topicWeaknesses.filter(hasWeaknessSignal)
    : [];

  return (
    <section className="card analytics-card topic-weakness-card-v2">
      <div className="section-title-row">
        <div>
          <h3>Topic Weakness Analytics</h3>
          <p className="muted">
            Network topics where validation failures are concentrated.
          </p>
        </div>

        <span className="badge neutral">{items.length} topics</span>
      </div>

      {items.length === 0 ? (
        <AnalyticsEmptyState
          title="No priority weaknesses detected."
          message="No topic has failed-check activity in the current analytics data."
        />
      ) : (
        <div className="topic-weakness-list">
          {items.map((item) => {
            const severity = normalizeSeverity(item.severity);

            return (
              <div className="topic-weakness-card" key={item.topic || item.label}>
                <div className="topic-weakness-header">
                  <div>
                    <strong>{item.label || item.topic || "Unknown topic"}</strong>
                    <p className="muted">
                      {formatNumber(item.fail_count)} failed checks out of {formatNumber(item.attempt_count)} attempts
                    </p>
                  </div>

                  <span className={`badge ${severity}`}>
                    {severity}
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

                <div className="analytics-bar-meta analytics-bar-meta-v2">
                  <span>Failure Rate: {formatNumber(item.failure_rate)}%</span>
                  <span>Average Score: {formatNumber(item.average_score, "-")}</span>
                  <span>Topic Key: {item.topic || "-"}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

export default TopicWeaknessList;
