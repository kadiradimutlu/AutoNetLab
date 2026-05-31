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
    return "fail";
  }

  if (["created", "deployed", "active", "validated"].includes(normalizedStatus)) {
    return "medium";
  }

  if (["finished", "destroyed"].includes(normalizedStatus)) {
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
    return "pass";
  }

  if (passed === false) {
    return "fail";
  }

  return "neutral";
}

function getLastActivityAt(session) {
  return session.completed_at || session.updated_at || session.created_at;
}

function getScenarioValue(session) {
  return session.scenario_id || session.scenario || session.scenario_name || "-";
}

function getTopologyValue(session) {
  return session.topology_template || session.topology_name || session.topology || "-";
}

function RecentSessionsTable({ sessions }) {
  const items = Array.isArray(sessions) ? sessions : [];

  return (
    <section className="card analytics-card recent-sessions-card-v2">
      <div className="section-title-row">
        <div>
          <h3>Recent Sessions</h3>
          <p className="muted">
            Latest student lab sessions with scenario and topology context.
          </p>
        </div>
      </div>

      {items.length === 0 ? (
        <AnalyticsEmptyState
          title="No recent sessions yet."
          message="Recent sessions will appear after students create lab sessions."
        />
      ) : (
        <div className="analytics-table-wrapper">
          <table className="analytics-table analytics-table-wide">
            <thead>
              <tr>
                <th>Session</th>
                <th>Student</th>
                <th>Scenario</th>
                <th>Topology</th>
                <th>Difficulty</th>
                <th>Status</th>
                <th>Score</th>
                <th>Result</th>
                <th>Last Activity</th>
              </tr>
            </thead>

            <tbody>
              {items.map((session) => (
                <tr key={session.session_id}>
                  <td>{session.session_id}</td>
                  <td>{session.student_id || "-"}</td>
                  <td>
                    <span className="analytics-code-pill">{getScenarioValue(session)}</span>
                  </td>
                  <td>
                    <span className="analytics-code-pill neutral">{getTopologyValue(session)}</span>
                  </td>
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
                  <td>{formatScore(session.score)}</td>
                  <td>
                    <span className={`badge ${getResultClass(session.passed)}`}>
                      {getResultLabel(session.passed)}
                    </span>
                  </td>
                  <td>{formatDate(getLastActivityAt(session))}</td>
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
