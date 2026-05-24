import AnalyticsEmptyState from "./AnalyticsEmptyState";

function formatDifficultyLabel(value) {
  if (!value) {
    return "-";
  }

  return value.charAt(0).toUpperCase() + value.slice(1);
}

function getBarWidth(value, maxValue) {
  if (!value || !maxValue) {
    return "0%";
  }

  return `${Math.min((value / maxValue) * 100, 100)}%`;
}

function DifficultyDistributionChart({ distribution }) {
  const items = Array.isArray(distribution) ? distribution : [];
  const maxSessionCount = Math.max(
    ...items.map((item) => item.session_count || 0),
    1
  );

  return (
    <section className="card analytics-card">
      <div className="section-title-row">
        <div>
          <h3>Difficulty Distribution</h3>
          <p className="muted">
            Lab sessions grouped by difficulty level.
          </p>
        </div>
      </div>

      {items.length === 0 ? (
        <AnalyticsEmptyState
          title="No difficulty data yet."
          message="Difficulty distribution will be available after lab sessions are created."
        />
      ) : (
        <div className="analytics-bar-list">
          {items.map((item) => (
            <div className="analytics-bar-row" key={item.difficulty}>
              <div className="analytics-bar-header">
                <div>
                  <span className={`badge ${item.difficulty}`}>
                    {formatDifficultyLabel(item.difficulty)}
                  </span>
                </div>

                <strong>{item.session_count} sessions</strong>
              </div>

              <div className="analytics-bar-track">
                <div
                  className="analytics-bar-fill"
                  style={{
                    "--bar-width": getBarWidth(
                      item.session_count,
                      maxSessionCount
                    )
                  }}
                />
              </div>

              <div className="analytics-bar-meta">
                <span>Completed: {item.completed_count}</span>
                <span>
                  Average Score: {Number(item.average_score || 0).toFixed(1)}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

export default DifficultyDistributionChart;