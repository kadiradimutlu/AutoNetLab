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
  return formatNumber(value, "-");
}

function getArrayCount(value) {
  return Array.isArray(value) ? value.length : 0;
}

function getCleanupIncidentCount(summary) {
  const incidents = summary?.cleanup_error_incidents;

  if (Array.isArray(incidents)) {
    return incidents.length;
  }

  const numericValue = Number(
    incidents ??
      summary?.cleanup_error_incident_count ??
      summary?.cleanup_incident_count ??
      summary?.error_incident_count ??
      0
  );

  return Number.isNaN(numericValue) ? 0 : numericValue;
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
      title: "Average Fault Score",
      value: formatScore(summary?.average_score),
      helper: "Fault resolution score range: 0-100"
    },
    {
      title: "Pass Rate",
      value: formatPercent(summary?.pass_rate),
      helper: "Passed sessions / completed sessions"
    },
    {
      title: "Scenarios Tracked",
      value: formatNumber(getArrayCount(summary?.scenario_performance)),
      helper: "Scenario-level training coverage"
    },
    {
      title: "Cleanup/Error Incidents",
      value: formatNumber(getCleanupIncidentCount(summary)),
      helper: "Labs requiring runtime cleanup attention"
    }
  ];

  return (
    <section className="card analytics-summary-card analytics-summary-card-v2">
      <div className="section-title-row">
        <div>
          <h3>Analytics Summary</h3>
          <p className="muted">
            Class-level session, scenario, fault-score, pass-rate, and cleanup overview.
          </p>
        </div>
      </div>

      <div className="analytics-summary-metric-grid analytics-summary-metric-grid-v2">
        {cards.map((card) => (
          <div className="analytics-summary-metric" key={card.title}>
            <span className="analytics-summary-metric-label">{card.title}</span>
            <strong className="analytics-summary-metric-value">{card.value}</strong>
            <p className="muted analytics-summary-metric-helper">{card.helper}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

export default AnalyticsSummaryCards;
