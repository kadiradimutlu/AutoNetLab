function clampScore(value, fallback = 0) {
  const numericValue = Number(value);

  if (Number.isNaN(numericValue)) {
    return fallback;
  }

  return Math.min(Math.max(Math.round(numericValue), 0), 100);
}

function getNumber(value, fallback = 0) {
  const numericValue = Number(value);

  if (Number.isNaN(numericValue)) {
    return fallback;
  }

  return numericValue;
}

function normalizeList(value) {
  if (!value) {
    return [];
  }

  if (Array.isArray(value)) {
    return value.filter(Boolean);
  }

  if (typeof value === "object") {
    return Object.values(value).filter(Boolean);
  }

  return [value];
}

function formatTopic(topic) {
  return String(topic || "")
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function getCheckTitle(check, index) {
  return (
    check?.label ||
    check?.name ||
    check?.check_name ||
    check?.check_id ||
    check?.id ||
    `Network check ${index + 1}`
  );
}

function getCheckDescription(check) {
  return (
    check?.description ||
    check?.message ||
    check?.hint ||
    check?.detail ||
    "No additional diagnostic detail provided."
  );
}

function isCheckPassed(check) {
  if (typeof check?.passed === "boolean") {
    return check.passed;
  }

  const status = String(check?.status || check?.result || "").toLowerCase();
  return status === "pass" || status === "passed" || status === "ok" || status === "success";
}

function NetworkHealthDetails({ validationResult }) {
  const checks = normalizeList(validationResult?.checks);
  const totalChecks = getNumber(
    validationResult?.network_total_checks ?? validationResult?.total_checks,
    checks.length
  );
  const passedChecks = getNumber(
    validationResult?.network_passed_checks ?? validationResult?.passed_checks,
    checks.filter(isCheckPassed).length
  );
  const failedChecks = getNumber(
    validationResult?.network_failed_checks ?? validationResult?.failed_checks,
    Math.max(totalChecks - passedChecks, 0)
  );
  const networkHealthScore = clampScore(
    validationResult?.network_health_score,
    totalChecks ? Math.round((passedChecks / totalChecks) * 100) : 0
  );
  const faultResolutionScore = clampScore(
    validationResult?.fault_resolution_score ?? validationResult?.score,
    0
  );
  const affectedTopics = normalizeList(validationResult?.affected_topics || validationResult?.affectedTopics);
  const failedTopics = normalizeList(validationResult?.failed_topics || validationResult?.failedTopics);
  const resolvedTopics = normalizeList(validationResult?.resolved_topics || validationResult?.resolvedTopics);

  return (
    <div className="network-health-details">
      <div className="section-title-row">
        <div>
          <h3>Network Health</h3>
          <p className="muted">
            Full network diagnostics for the current validation run. This view separates
            overall network checks from injected fault resolution.
          </p>
        </div>
      </div>

      <div className="recommendation-meta-grid recommendation-meta-grid-v2">
        <div>
          <span className="muted">Network Health Score</span>
          <strong>{networkHealthScore}/100</strong>
          <p>Overall status of the full validation check set.</p>
        </div>

        <div>
          <span className="muted">Fault Resolution Score</span>
          <strong>{faultResolutionScore}/100</strong>
          <p>Primary student score based on injected fault resolution.</p>
        </div>

        <div>
          <span className="muted">Full Network Checks</span>
          <strong>{passedChecks}/{totalChecks} passed</strong>
          <p>{failedChecks} check{failedChecks === 1 ? "" : "s"} still failing.</p>
        </div>
      </div>

      <div className="recommendation-topic-panel">
        <h4>Topic Diagnostics</h4>

        <div className="recommendation-meta-grid recommendation-meta-grid-v2">
          <div>
            <span className="muted">Affected Topics</span>
            <strong>{affectedTopics.length || "None reported"}</strong>
            <p>{affectedTopics.map(formatTopic).join(", ") || "No affected topic metadata reported."}</p>
          </div>

          <div>
            <span className="muted">Failed Topics</span>
            <strong>{failedTopics.length || "None"}</strong>
            <p>{failedTopics.map(formatTopic).join(", ") || "No failed topic metadata reported."}</p>
          </div>

          <div>
            <span className="muted">Resolved Topics</span>
            <strong>{resolvedTopics.length || "None"}</strong>
            <p>{resolvedTopics.map(formatTopic).join(", ") || "No resolved topic metadata reported."}</p>
          </div>
        </div>
      </div>

      <div className="validation-check-list">
        <h4>Full Network Check Details</h4>

        {checks.length === 0 ? (
          <p className="muted">No detailed network checks were returned for this validation run.</p>
        ) : (
          <ul>
            {checks.map((check, index) => {
              const passed = isCheckPassed(check);

              return (
                <li className={`validation-check-item ${passed ? "pass" : "fail"}`} key={`${getCheckTitle(check, index)}-${index}`}>
                  <div>
                    <strong>{getCheckTitle(check, index)}</strong>
                    <p>{getCheckDescription(check)}</p>
                  </div>
                  <span className={`badge ${passed ? "pass" : "fail"}`}>
                    {passed ? "PASS" : "FAIL"}
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}

export default NetworkHealthDetails;
