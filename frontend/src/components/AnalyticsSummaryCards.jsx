function formatNumber(value) {
  if (value === null || value === undefined) {
    return "-";
  }

  return Number(value).toLocaleString("en-US");
}

function formatPercent(value) {
  if (value === null || value === undefined) {
    return "-";
  }

  return `${Number(value).toFixed(1)}%`;
}

function formatScore(value) {
  if (value === null || value === undefined) {
    return "-";
  }

  return Number(value).toFixed(1);
}

function AnalyticsSummaryCards({ summary }) {
  const cards = [
    {
      title: "Total Sessions",
      value: formatNumber(summary?.total_sessions),
      helper: "All created lab sessions"
    },
    {
      title: "Completed Sessions",
      value: formatNumber(summary?.completed_sessions),
      helper: "Validated or finished sessions"
    },
    {
      title: "Average Score",
      value: formatScore(summary?.average_score),
      helper: "Score range: 0–100"
    },
    {
      title: "Pass Rate",
      value: formatPercent(summary?.pass_rate),
      helper: "Passed sessions / completed sessions"
    }
  ];

  return (
    <section className="grid analytics-summary-grid">
      {cards.map((card) => (
        <div className="card analytics-stat-card" key={card.title}>
          <span className="muted">{card.title}</span>
          <div className="stat-value">{card.value}</div>
          <p className="muted">{card.helper}</p>
        </div>
      ))}
    </section>
  );
}

export default AnalyticsSummaryCards;