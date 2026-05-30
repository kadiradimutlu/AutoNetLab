import AnalyticsEmptyState from "./AnalyticsEmptyState";

function formatDifficultyLabel(value) {
  if (!value) {
    return "-";
  }

  return String(value).charAt(0).toUpperCase() + String(value).slice(1);
}

function getBarWidth(value, maxValue) {
  if (!value || !maxValue) {
    return "0%";
  }

  return `${Math.min((value / maxValue) * 100, 100)}%`;
}

function formatPercent(value) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }

  const numericValue = Number(value);

  if (Number.isNaN(numericValue)) {
    return "-";
  }

  return `${numericValue.toFixed(1)}%`;
}

function formatNumber(value, fallback = "-") {
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

function normalizeDifficultyItem(item) {
  const safeItem = item && typeof item === "object" ? item : {};

  return {
    difficulty: safeItem.difficulty || safeItem.label || safeItem.name || "unknown",
    session_count:
      safeItem.session_count ??
      safeItem.total_sessions ??
      safeItem.sessions ??
      0,
    completed_count:
      safeItem.completed_count ??
      safeItem.completed_sessions ??
      0,
    passed_count:
      safeItem.passed_count ??
      safeItem.passed_sessions ??
      0,
    average_score:
      safeItem.average_score ??
      safeItem.avg_score ??
      null,
    pass_rate:
      safeItem.pass_rate ??
      safeItem.success_rate ??
      null
  };
}

function DifficultyDistributionChart({ distribution }) {
  const items = Array.isArray(distribution)
    ? distribution.map((item) => normalizeDifficultyItem(item))
    : [];
  const maxSessionCount = Math.max(
    ...items.map((item) => Number(item.session_count) || 0),
    1
  );

  return (
    <section className="card analytics-card difficulty-performance-card">
      <div className="section-title-row">
        <div>
          <h3>Difficulty Performance</h3>
          <p className="muted">
            Lab outcomes grouped by difficulty, pass rate, and average score.
          </p>
        </div>
      </div>

      {items.length === 0 ? (
        <AnalyticsEmptyState
          title="No difficulty data yet."
          message="Difficulty performance will be available after lab sessions are validated."
        />
      ) : (
        <div className="analytics-bar-list">
          {items.map((item) => (
            <div className="analytics-bar-row difficulty-performance-row" key={item.difficulty}>
              <div className="analytics-bar-header">
                <div>
                  <span className={`badge ${item.difficulty}`}>
                    {formatDifficultyLabel(item.difficulty)}
                  </span>
                </div>

                <strong>{formatNumber(item.session_count, "0")} sessions</strong>
              </div>

              <div className="analytics-bar-track">
                <div
                  className="analytics-bar-fill"
                  style={{
                    "--bar-width": getBarWidth(
                      Number(item.session_count) || 0,
                      maxSessionCount
                    )
                  }}
                />
              </div>

              <div className="analytics-bar-meta analytics-bar-meta-v2">
                <span>Completed: {formatNumber(item.completed_count, "0")}</span>
                <span>Passed: {formatNumber(item.passed_count, "0")}</span>
                <span>Pass Rate: {formatPercent(item.pass_rate)}</span>
                <span>Average Score: {formatNumber(item.average_score)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

export default DifficultyDistributionChart;
