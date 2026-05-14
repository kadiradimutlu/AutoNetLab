import MessageBox from "./MessageBox";

function formatBoolean(value) {
  if (value === true) {
    return "Ready";
  }

  if (value === false) {
    return "Not Ready";
  }

  return "Unknown";
}

function getBooleanBadgeClass(value) {
  if (value === true) {
    return "pass";
  }

  if (value === false) {
    return "fail";
  }

  return "neutral";
}

function getSafeText(value, fallback = "-") {
  if (value === undefined || value === null || value === "") {
    return fallback;
  }

  return String(value);
}

function RuntimeMetricCard({ label, value, ok }) {
  return (
    <div className="runtime-metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
      {ok !== undefined && (
        <span className={`badge ${getBooleanBadgeClass(ok)}`}>
          {formatBoolean(ok)}
        </span>
      )}
    </div>
  );
}

function RuntimeChecksList({ checks = [] }) {
  if (!Array.isArray(checks) || checks.length === 0) {
    return (
      <p className="muted">
        Runtime checks will appear after the backend readiness endpoint responds.
      </p>
    );
  }

  return (
    <div className="runtime-check-list">
      {checks.map((check, index) => (
        <div
          className={`runtime-check-item ${check.ok ? "ok" : "failed"}`}
          key={`${check.name || "check"}-${index}`}
        >
          <span className={`badge ${check.ok ? "pass" : "fail"}`}>
            {check.ok ? "OK" : "ISSUE"}
          </span>

          <div>
            <strong>{getSafeText(check.name, `Check ${index + 1}`)}</strong>
            <p>{getSafeText(check.message, "No detail message returned.")}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

function RuntimeReadinessCard({
  readiness,
  isLoading,
  errorMessage,
  errorDetails,
  lastCheckedAt,
  onRefresh
}) {
  const isReady = readiness?.ready === true;

  return (
    <section className={`card runtime-readiness-card ${isReady ? "ready" : "not-ready"}`}>
      <div className="section-title-row">
        <div>
          <h3>Runtime Readiness</h3>
          <p className="muted">
            Demo preflight status for Docker, Containerlab, templates, and Web CLI runtime.
          </p>
        </div>

        <span className={`badge ${isReady ? "pass" : "fail"}`}>
          {isReady ? "READY" : "NOT READY"}
        </span>
      </div>

      {errorMessage && (
        <>
          <MessageBox
            type="error"
            title="Runtime readiness check is unavailable"
            message={errorMessage}
          />

          {errorDetails && (
            <div className="technical-detail-box">
              <strong>Technical detail</strong>
              <p>{errorDetails}</p>
            </div>
          )}
        </>
      )}

      {!errorMessage && (
        <MessageBox
          type={isReady ? "success" : "info"}
          title={isReady ? "Demo runtime is ready" : "Demo runtime needs attention"}
          message={
            readiness?.message ||
            "Runtime readiness check has not returned a message yet."
          }
        />
      )}

      <div className="runtime-readiness-actions">
        <button
          className="secondary-button"
          onClick={onRefresh}
          disabled={isLoading}
          type="button"
        >
          {isLoading ? "Checking..." : "Refresh Runtime Readiness"}
        </button>

        <span className="muted">
          Last checked: {lastCheckedAt ? lastCheckedAt.toLocaleString("en-US") : "Not checked yet"}
        </span>
      </div>

      <div className="runtime-readiness-grid">
        <RuntimeMetricCard
          label="Overall Status"
          value={isReady ? "Ready" : "Not Ready"}
          ok={readiness?.ready}
        />

        <RuntimeMetricCard
          label="Docker Available"
          value={formatBoolean(readiness?.docker_available)}
          ok={readiness?.docker_available}
        />

        <RuntimeMetricCard
          label="Docker Daemon"
          value={formatBoolean(readiness?.docker_ps_ok)}
          ok={readiness?.docker_ps_ok}
        />

        <RuntimeMetricCard
          label="Containerlab"
          value={formatBoolean(readiness?.containerlab_available)}
          ok={readiness?.containerlab_available}
        />

        <RuntimeMetricCard
          label="Templates Directory"
          value={formatBoolean(readiness?.templates_dir_exists)}
          ok={readiness?.templates_dir_exists}
        />

        <RuntimeMetricCard
          label="Generated Directory"
          value={formatBoolean(readiness?.generated_dir_exists)}
          ok={readiness?.generated_dir_exists}
        />

        <RuntimeMetricCard
          label="Current CLI Mode"
          value={getSafeText(readiness?.current_mode)}
        />

        <RuntimeMetricCard
          label="Fallback Mode"
          value={getSafeText(readiness?.fallback_mode)}
        />
      </div>

      <div className="runtime-info-grid">
        <div>
          <span>Platform</span>
          <strong>{getSafeText(readiness?.platform)}</strong>
        </div>

        <div>
          <span>Platform Release</span>
          <strong>{getSafeText(readiness?.platform_release)}</strong>
        </div>

        <div>
          <span>Recommended Backend Environment</span>
          <strong>{getSafeText(readiness?.recommended_backend_environment)}</strong>
        </div>

        <div>
          <span>Docker Version</span>
          <strong>{getSafeText(readiness?.docker_version)}</strong>
        </div>

        <div>
          <span>Containerlab Version</span>
          <strong>{getSafeText(readiness?.containerlab_version)}</strong>
        </div>

        <div>
          <span>Project Root</span>
          <strong>{getSafeText(readiness?.project_root)}</strong>
        </div>

        <div>
          <span>Templates Directory</span>
          <strong>{getSafeText(readiness?.templates_dir)}</strong>
        </div>

        <div>
          <span>Generated Directory</span>
          <strong>{getSafeText(readiness?.generated_dir)}</strong>
        </div>
      </div>

      <div className="runtime-check-section">
        <div className="section-title-row compact">
          <div>
            <h4>Preflight Checks</h4>
            <p className="muted">
              These checks help distinguish frontend issues from Docker or Containerlab runtime issues.
            </p>
          </div>

          <span className="badge neutral">
            {Array.isArray(readiness?.checks) ? readiness.checks.length : 0} checks
          </span>
        </div>

        <RuntimeChecksList checks={readiness?.checks || []} />
      </div>
    </section>
  );
}

export default RuntimeReadinessCard;
