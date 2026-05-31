import AnalyticsEmptyState from "./AnalyticsEmptyState";

function formatDifficultyLabel(value) {
  if (!value) {
    return "-";
  }

  return String(value).charAt(0).toUpperCase() + String(value).slice(1);
}

function formatDate(value) {
  if (!value) {
    return "-";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString("en-US", {
    dateStyle: "short",
    timeStyle: "short"
  });
}

function formatScore(value) {
  if (value === null || value === undefined) {
    return "-";
  }

  return value;
}

function formatTitleCase(value) {
  const normalizedValue = String(value || "").replace(/_/g, " ").trim();

  if (!normalizedValue) {
    return "-";
  }

  return normalizedValue
    .split(" ")
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

function getLifecycleStatusLabel(status) {
  const normalizedStatus = String(status || "").toLowerCase();

  const statusLabels = {
    created: "Created",
    deployed: "Deployed",
    active: "Active",
    validated: "Validated",
    finished: "Finished",
    destroyed: "Destroyed",
    error: "Error"
  };

  return statusLabels[normalizedStatus] || formatTitleCase(status);
}

function getLifecycleStatusClass(status) {
  const normalizedStatus = String(status || "").toLowerCase();

  if (normalizedStatus === "error") {
    return "status-error";
  }

  if (normalizedStatus === "created") {
    return "status-created";
  }

  if (["deployed", "active"].includes(normalizedStatus)) {
    return "status-active";
  }

  if (normalizedStatus === "validated") {
    return "status-validated";
  }

  if (normalizedStatus === "finished") {
    return "finished";
  }

  if (normalizedStatus === "destroyed") {
    return "neutral";
  }

  return "neutral";
}

function getResultLabel(passed) {
  if (passed === true) {
    return "PASS";
  }

  if (passed === false) {
    return "FAIL";
  }

  return "Not Validated";
}

function getResultClass(passed) {
  if (passed === true) {
    return "result-pass";
  }

  if (passed === false) {
    return "result-fail";
  }

  return "result-pending";
}

function getLastActivityAt(session) {
  return session.completed_at || session.updated_at || session.created_at;
}

function getScenarioValue(session) {
  return session.scenario_id || session.scenario || session.scenario_name || "-";
}

const SCENARIO_TITLE_BY_ID = {
  "srl-edge-link": "Edge Link Troubleshooting",
  "branch-static-routing": "Branch Static Routing",
  "campus-core-routing": "Campus Core Troubleshooting",
  "campus-core-static-routing": "Campus Core Troubleshooting",
  "srl-basic-link": "Edge Link Troubleshooting"
};

function getScenarioDisplayTitle(session) {
  const rawValue = getScenarioValue(session);

  return SCENARIO_TITLE_BY_ID[rawValue] || rawValue || "Scenario not reported";
}

function getScenarioTitleLines(title) {
  const normalizedTitle = String(title || "").trim();

  const fixedLines = {
    "Edge Link Troubleshooting": ["Edge Link", "Troubleshooting"],
    "Branch Static Routing": ["Branch Static", "Routing"],
    "Campus Core Troubleshooting": ["Campus Core", "Troubleshooting"]
  };

  if (fixedLines[normalizedTitle]) {
    return fixedLines[normalizedTitle];
  }

  if (!normalizedTitle) {
    return ["Scenario not reported"];
  }

  return [normalizedTitle];
}

function ScenarioTitleLines({ title }) {
  return (
    <>
      {getScenarioTitleLines(title).map((line) => (
        <span key={line}>{line}</span>
      ))}
    </>
  );
}

function getFaultScore(session) {
  return session.fault_resolution_score ?? session.score ?? null;
}

function RecentSessionsTable({ sessions, onViewDetails }) {
  const items = Array.isArray(sessions) ? sessions : [];

  return (
    <section className="card analytics-card recent-sessions-card-v2">
      <div className="section-title-row">
        <div>
          <h3>Recent Sessions</h3>
          <p className="muted">
            Latest student lab sessions with scenario context.
          </p>
        </div>

        <span className="badge neutral">{items.length} sessions</span>
      </div>

      {items.length === 0 ? (
        <AnalyticsEmptyState
          title="No recent sessions yet."
          message="Recent sessions will appear after students create lab sessions."
        />
      ) : (
        <div className="analytics-table-wrapper analytics-recent-sessions-scroll">
          <table className="analytics-table analytics-table-wide analytics-recent-sessions-table">
            <thead>
              <tr>
                <th>Session</th>
                <th>Student</th>
                <th>Difficulty</th>
                <th>Status</th>
                <th>Fault Score</th>
                <th>Result</th>
                <th>Last Activity</th>
                <th>Action</th>
              </tr>
            </thead>

            <tbody>
              {items.map((session) => (
                <tr key={session.session_id}>
                  <td>
                    <div className="session-title-cell">
                      <strong>{session.session_id || "-"}</strong>
                      <ScenarioTitleLines title={getScenarioDisplayTitle(session)} />
                    </div>
                  </td>
                  <td>{session.student_id || "-"}</td>
                  <td>
                    <span className={`badge ${session.difficulty}`}>
                      {formatDifficultyLabel(session.difficulty)}
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${getLifecycleStatusClass(session.status)}`}>
                      {getLifecycleStatusLabel(session.status)}
                    </span>
                  </td>
                  <td>{formatScore(getFaultScore(session))}</td>
                  <td>
                    <span className={`badge ${getResultClass(session.passed)}`}>
                      {getResultLabel(session.passed)}
                    </span>
                  </td>
                  <td>{formatDate(getLastActivityAt(session))}</td>
                  <td>
                    <button
                      className="secondary-button table-action-button table-action-button-stacked"
                      onClick={() => onViewDetails?.(session)}
                      type="button"
                      aria-label={`View details for ${session.session_id}`}
                    >
                      <span>View</span>
                      <span>Details</span>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export default RecentSessionsTable;
