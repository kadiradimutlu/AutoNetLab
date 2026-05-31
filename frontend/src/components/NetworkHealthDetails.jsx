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

function TopicList({ items, emptyText }) {
  if (!items.length) {
    return <p className="muted">{emptyText}</p>;
  }

  return (
    <div className="network-health-chip-list">
      {items.map((item) => (
        <span className="network-health-chip" key={String(item)}>
          {formatTopic(item)}
        </span>
      ))}
    </div>
  );
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
  const healthStatus = failedChecks > 0 ? "Needs Review" : "Healthy";
  const healthClass = failedChecks > 0 ? "fail" : "pass";

  return (
    <div className="network-health-details">
      <section className={`network-health-hero network-health-details-card ${healthClass}`}>
        <div>
          <span className={`badge ${healthClass}`}>{healthStatus}</span>
          <h3>Network Health</h3>
          <p>
            Full network diagnostics for the current validation run. This view separates
            overall network checks from injected fault resolution.
          </p>
        </div>

        <div className="network-health-hero-score-grid">
          <div className="network-health-score-card">
            <span>Network Health Score</span>
            <strong>{networkHealthScore}/100</strong>
            <p>Overall status of the full validation check set.</p>
          </div>

          <div className="network-health-score-card">
            <span>Fault Resolution Score</span>
            <strong>{faultResolutionScore}/100</strong>
            <p>Primary student score based on injected fault resolution.</p>
          </div>
        </div>
      </section>

      <section className="network-health-details-card">
        <div className="section-title-row">
          <div>
            <h4>Score Breakdown</h4>
            <p className="muted">
              Network Health summarizes the full validation checklist. Fault Resolution
              remains the primary score for injected fault progress.
            </p>
          </div>
        </div>

        <div className="network-health-grid">
          <div className="network-health-metric-card">
            <span>Full Network Checks</span>
            <strong>{passedChecks}/{totalChecks} passed</strong>
            <p>{failedChecks} check{failedChecks === 1 ? "" : "s"} still failing.</p>
          </div>

          <div className="network-health-metric-card pass">
            <span>Passed Checks</span>
            <strong>{passedChecks}</strong>
            <p>Checks currently matching the expected network state.</p>
          </div>

          <div className={`network-health-metric-card ${failedChecks > 0 ? "fail" : "pass"}`}>
            <span>Failed Checks</span>
            <strong>{failedChecks}</strong>
            <p>{failedChecks > 0 ? "Review the failed checks below." : "No failed checks reported."}</p>
          </div>
        </div>
      </section>

      <section className="network-health-details-card">
        <div className="section-title-row">
          <div>
            <h4>Topic Diagnostics</h4>
            <p className="muted">
              Topic metadata groups the validation result into troubleshooting areas.
            </p>
          </div>
        </div>

        <div className="network-health-grid">
          <div className="network-health-metric-card">
            <span>Affected Topics</span>
            <strong>{affectedTopics.length || "None reported"}</strong>
            <TopicList
              items={affectedTopics}
              emptyText="No affected topic metadata reported."
            />
          </div>

          <div className={`network-health-metric-card ${failedTopics.length ? "fail" : "pass"}`}>
            <span>Failed Topics</span>
            <strong>{failedTopics.length || "None"}</strong>
            <TopicList
              items={failedTopics}
              emptyText="No failed topic metadata reported."
            />
          </div>

          <div className="network-health-metric-card pass">
            <span>Resolved Topics</span>
            <strong>{resolvedTopics.length || "None"}</strong>
            <TopicList
              items={resolvedTopics}
              emptyText="No resolved topic metadata reported."
            />
          </div>
        </div>
      </section>

      <section className="network-health-details-card">
        <div className="section-title-row">
          <div>
            <h4>Full Network Check Details</h4>
            <p className="muted">
              Failed checks are highlighted first so the next troubleshooting step is easier to identify.
            </p>
          </div>
        </div>

        {checks.length === 0 ? (
          <p className="muted">No detailed network checks were returned for this validation run.</p>
        ) : (
          <ul className="network-health-check-list">
            {checks
              .map((check, index) => ({
                check,
                index,
                passed: isCheckPassed(check)
              }))
              .sort((left, right) => Number(left.passed) - Number(right.passed))
              .map(({ check, index, passed }) => (
                <li
                  className={`network-health-check-card ${passed ? "pass" : "fail"}`}
                  key={`${getCheckTitle(check, index)}-${index}`}
                >
                  <div>
                    <span className="network-health-check-label">Check {index + 1}</span>
                    <strong>{getCheckTitle(check, index)}</strong>
                    <p>{getCheckDescription(check)}</p>
                  </div>

                  <span className={`badge ${passed ? "pass" : "fail"}`}>
                    {passed ? "PASS" : "FAIL"}
                  </span>
                </li>
              ))}
          </ul>
        )}
      </section>
    </div>
  );
}

export default NetworkHealthDetails;
