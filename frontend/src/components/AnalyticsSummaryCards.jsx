function formatNumber(value) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }

  const numericValue = Number(value);

  if (Number.isNaN(numericValue)) {
    return "-";
  }

  return numericValue.toLocaleString("en-US");
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

function formatScore(value) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }

  const numericValue = Number(value);

  if (Number.isNaN(numericValue)) {
    return "-";
  }

  return numericValue.toFixed(1);
}

function AnalyticsSummaryCards({ summary }) {
  const cards = [
    {
      title: "Total Sessions",
      value: formatNumber(summary?.total_sessions),
      helper: "All tracked lab sessions"
    },
    {
      title: "Active Sessions",
      value: formatNumber(summary?.active_sessions),
      helper: "Labs still open for troubleshooting"
    },
    {
      title: "Completed Sessions",
      value: formatNumber(summary?.completed_sessions),
      helper: "Validated or finished sessions"
    },
    {
      title: "Passed Sessions",
      value: formatNumber(summary?.passed_sessions),
      helper: "Completed sessions with PASS result"
    },
    {
      title: "Average Score",
      value: formatScore(summary?.average_score),
      helper: "Score range: 0-100"
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