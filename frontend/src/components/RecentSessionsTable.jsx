import AnalyticsEmptyState from "./AnalyticsEmptyState";

function formatDifficultyLabel(value) {
  if (!value) {
    return "-";
  }

  return value.charAt(0).toUpperCase() + value.slice(1);
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

function getResultLabel(passed) {
  if (passed === true) {
    return "PASS";
  }

  if (passed === false) {
    return "FAIL";
  }

  return "Pending";
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

function RecentSessionsTable({ sessions }) {
  const items = Array.isArray(sessions) ? sessions : [];

  return (
    <section className="card analytics-card">
      <div className="section-title-row">
        <div>
          <h3>Recent Sessions</h3>
          <p className="muted">
            Latest student lab sessions and validation results.
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
          <table className="analytics-table">
            <thead>
              <tr>
                <th>Session ID</th>
                <th>Student</th>
                <th>Difficulty</th>
                <th>Status</th>
                <th>Score</th>
                <th>Result</th>
                <th>Completed At</th>
              </tr>
            </thead>

            <tbody>
              {items.map((session) => (
                <tr key={session.session_id}>
                  <td>{session.session_id}</td>
                  <td>{session.student_id || "-"}</td>
                  <td>
                    <span className={`badge ${session.difficulty}`}>
                      {formatDifficultyLabel(session.difficulty)}
                    </span>
                  </td>
                  <td>{session.status || "-"}</td>
                  <td>{formatScore(session.score)}</td>
                  <td>
                    <span className={`badge ${getResultClass(session.passed)}`}>
                      {getResultLabel(session.passed)}
                    </span>
                  </td>
                  <td>{formatDate(session.completed_at)}</td>
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