import MessageBox from "./MessageBox";

function getDisplayValue(value, fallback = "-") {
  if (value === undefined || value === null || value === "") {
    return fallback;
  }

  if (typeof value === "object") {
    return JSON.stringify(value);
  }

  return String(value);
}

function toReadableLabel(value) {
  return getDisplayValue(value)
    .replace(/_/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function normalizeStatus(check) {
  const rawStatus = String(check.status || "").toLowerCase();

  if (rawStatus.includes("pass") || rawStatus === "success") {
    return "pass";
  }

  if (rawStatus.includes("fail") || rawStatus === "error") {
    return "fail";
  }

  if (check.passed === true) {
    return "pass";
  }

  if (check.passed === false) {
    return "fail";
  }

  return "unknown";
}

function getStatusLabel(status) {
  if (status === "pass") {
    return "PASS";
  }

  if (status === "fail") {
    return "FAIL";
  }

  return "UNKNOWN";
}

function getStatusClass(status) {
  if (status === "pass") {
    return "pass";
  }

  if (status === "fail") {
    return "fail";
  }

  return "neutral";
}

function getCheckTitle(check, index) {
  return (
    check.description ||
    check.message ||
    check.check_id ||
    `Validation Check ${index + 1}`
  );
}

function getCheckPoints(check) {
  const points = check.points ?? check.score ?? 0;
  const maxPoints = check.max_points ?? check.maxPoints ?? 0;

  if (maxPoints) {
    return `${points}/${maxPoints}`;
  }

  return getDisplayValue(points, "0");
}

function groupChecksByTopic(checks) {
  return checks.reduce((groups, check) => {
    const topic = check.topic || check.category || "General";
    const key = String(topic);

    if (!groups[key]) {
      groups[key] = [];
    }

    groups[key].push(check);
    return groups;
  }, {});
}

function DebugEvidencePanel({ check }) {
  const hasDebugData =
    check.evidence ||
    check.observed_state ||
    check.expected_state ||
    check.failed_command_output;

  if (!hasDebugData) {
    return null;
  }

  return (
    <details className="debug-evidence-panel">
      <summary>Debug evidence</summary>

      {check.evidence && (
        <div>
          <span>Evidence</span>
          <pre>{getDisplayValue(check.evidence)}</pre>
        </div>
      )}

      {check.observed_state && (
        <div>
          <span>Observed State</span>
          <pre>{getDisplayValue(check.observed_state)}</pre>
        </div>
      )}

      {check.expected_state && (
        <div>
          <span>Expected State</span>
          <pre>{getDisplayValue(check.expected_state)}</pre>
        </div>
      )}

      {check.failed_command_output && (
        <div>
          <span>Failed Command Output</span>
          <pre>{getDisplayValue(check.failed_command_output)}</pre>
        </div>
      )}
    </details>
  );
}

function ValidationCheckList({
  checks = [],
  showDebugEvidence = false
}) {
  if (!checks.length) {
    return (
      <MessageBox
        type="empty"
        title="No check details"
        message="No checks list was found in the backend validation response."
      />
    );
  }

  const groupedChecks = groupChecksByTopic(checks);

  return (
    <div className="validation-topic-list">
      {Object.entries(groupedChecks).map(([topic, topicChecks]) => (
        <section className="validation-topic-group" key={topic}>
          <div className="validation-topic-header">
            <div>
              <span className="muted">Topic</span>
              <h4>{toReadableLabel(topic)}</h4>
            </div>

            <span className="badge neutral">
              {topicChecks.length} {topicChecks.length === 1 ? "check" : "checks"}
            </span>
          </div>

          <div className="result-list">
            {topicChecks.map((check, index) => {
              const status = normalizeStatus(check);

              return (
                <div
                  className={`list-item check-card ${
                    status === "pass" ? "passed-check-card" : "failed-check-card"
                  }`}
                  key={check.check_id || `${topic}-${index}`}
                >
                  <div className="result-title-row">
                    <div>
                      <strong>{getCheckTitle(check, index)}</strong>
                      <p className="muted">
                        Check ID: {getDisplayValue(check.check_id, `check-${index + 1}`)}
                      </p>
                    </div>

                    <span className={`badge ${getStatusClass(status)}`}>
                      {getStatusLabel(status)}
                    </span>
                  </div>

                  <div className="check-detail-grid advanced-check-grid">
                    <div>
                      <span>Topic</span>
                      <strong>{toReadableLabel(check.topic || topic)}</strong>
                    </div>

                    <div>
                      <span>Points</span>
                      <strong>{getCheckPoints(check)}</strong>
                    </div>

                    <div>
                      <span>Status</span>
                      <strong>{getStatusLabel(status)}</strong>
                    </div>

                    <div>
                      <span>Hint</span>
                      <strong>{getDisplayValue(check.hint || check.message, "Review this topic and re-check the device configuration.")}</strong>
                    </div>
                  </div>

                  {check.message && (
                    <p className="check-message">{check.message}</p>
                  )}

                  {showDebugEvidence && <DebugEvidencePanel check={check} />}
                </div>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}

export default ValidationCheckList;
