import MessageBox from "./MessageBox";

function getSafeText(value, fallback = "-") {
  if (value === undefined || value === null || value === "") {
    return fallback;
  }

  return String(value);
}

function formatEngine(engine) {
  const normalizedEngine = String(engine || "").toLowerCase();

  if (normalizedEngine.includes("postgres")) {
    return "PostgreSQL";
  }

  if (normalizedEngine.includes("sqlite")) {
    return "SQLite";
  }

  return engine ? String(engine) : "Unknown";
}

function DatabaseReadinessCard({
  readiness,
  isLoading,
  errorMessage,
  errorDetails,
  lastCheckedAt,
  onRefresh
}) {
  const isReady = readiness?.ready === true;
  const engineLabel = formatEngine(readiness?.database_engine);
  const connectionLabel = isReady ? "OK" : "Failed";
  const databaseUrl = getSafeText(readiness?.database_url);
  const backendError = getSafeText(readiness?.error, "");

  return (
    <section className={`card database-readiness-card ${isReady ? "ready" : "not-ready"}`}>
      <div className="section-title-row">
        <div>
          <h3>Database Readiness</h3>
          <p className="muted">
            PostgreSQL persistence visibility for lab sessions, validation results, and recommendations.
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
            title="Database readiness check is unavailable"
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
          type={isReady ? "success" : "error"}
          title={isReady ? "Database Ready" : "Database Not Ready"}
          message={
            isReady
              ? `${engineLabel} connection is healthy. Persistence layer is active.`
              : readiness?.message || "Database connection is not ready."
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
          {isLoading ? "Checking..." : "Refresh Database Readiness"}
        </button>

        <span className="muted">
          Last checked: {lastCheckedAt ? lastCheckedAt.toLocaleString("en-US") : "Not checked yet"}
        </span>
      </div>

      <div className="database-readiness-grid">
        <div className="runtime-metric-card">
          <span>Database Status</span>
          <strong>{isReady ? "Ready" : "Not Ready"}</strong>
          <span className={`badge ${isReady ? "pass" : "fail"}`}>
            {isReady ? "Ready" : "Not Ready"}
          </span>
        </div>

        <div className="runtime-metric-card">
          <span>Engine</span>
          <strong>{engineLabel}</strong>
        </div>

        <div className="runtime-metric-card">
          <span>Connection</span>
          <strong>{connectionLabel}</strong>
          <span className={`badge ${isReady ? "pass" : "fail"}`}>
            {connectionLabel}
          </span>
        </div>

        <div className="runtime-metric-card">
          <span>Persistence Layer</span>
          <strong>{isReady ? "Active" : "Unavailable"}</strong>
          <span className={`badge ${isReady ? "pass" : "fail"}`}>
            {isReady ? "Active" : "Issue"}
          </span>
        </div>
      </div>

      <div className="database-detail-grid">
        <div>
          <span>Message</span>
          <strong>{getSafeText(readiness?.message, "No database readiness message returned.")}</strong>
        </div>

        <div>
          <span>Database URL</span>
          <strong>{databaseUrl}</strong>
        </div>

        <div>
          <span>Error</span>
          <strong>{backendError || "None"}</strong>
        </div>
      </div>
    </section>
  );
}

export default DatabaseReadinessCard;
