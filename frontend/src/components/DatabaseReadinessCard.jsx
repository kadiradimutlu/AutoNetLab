import { useState } from "react";
import MessageBox from "./MessageBox";

function getSafeText(value, fallback = "-") {
  if (value === undefined || value === null || value === "") {
    return fallback;
  }

  return String(value);
}

function getDatabaseStatus(readiness, isLoading, errorMessage) {
  if (isLoading) {
    return {
      label: "Checking",
      badgeClass: "neutral",
      message: "Database status is being refreshed."
    };
  }

  if (errorMessage) {
    return {
      label: "Unavailable",
      badgeClass: "fail",
      message: "Database status could not be checked. Review diagnostics if needed."
    };
  }

  if (readiness?.ready === true) {
    return {
      label: "Ready",
      badgeClass: "pass",
      message: "Database persistence is active and analytics data can be stored."
    };
  }

  if (readiness?.ready === false) {
    return {
      label: "Needs Attention",
      badgeClass: "fail",
      message: "Database persistence needs attention before analytics can be trusted."
    };
  }

  return {
    label: "Not Checked",
    badgeClass: "neutral",
    message: "Refresh database status to verify persistence."
  };
}

function maskDatabaseUrl(value) {
  const text = getSafeText(value, "Not reported");

  if (text === "Not reported") {
    return text;
  }

  return text
    .replace(/:\/\/([^:@/]+):([^@/]+)@/, "://***:***@")
    .replace(/password=[^&\s]+/i, "password=***");
}

function DatabaseMetricCard({ label, value, badgeClass, badgeLabel, helper }) {
  return (
    <div className="runtime-metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
      {badgeLabel && (
        <span className={`badge ${badgeClass}`}>
          {badgeLabel}
        </span>
      )}
      {helper && <p className="muted">{helper}</p>}
    </div>
  );
}

function DiagnosticRow({ label, value }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{getSafeText(value)}</strong>
    </div>
  );
}

function DatabaseReadinessCard({
  readiness,
  isLoading,
  errorMessage,
  errorDetails,
  lastCheckedAt,
  onRefresh
}) {
  const [showDiagnostics, setShowDiagnostics] = useState(false);
  const status = getDatabaseStatus(readiness, isLoading, errorMessage);
  const isReady = readiness?.ready === true;
  const engineLabel = getSafeText(readiness?.database_engine, "Not reported");
  const connectionLabel = isReady ? "Connected" : readiness?.ready === false ? "Needs Attention" : "Unknown";
  const reportedError = readiness?.error || errorDetails || "";

  return (
    <section className={`card runtime-readiness-card database-readiness-card ${isReady ? "ready" : "not-ready"}`}>
      <div className="section-title-row">
        <div>
          <h3>Database Readiness</h3>
          <p className="muted">
            Persistence status for lab history, validation results, recommendations, and analytics.
          </p>
        </div>

        <span className={`badge ${status.badgeClass}`}>
          {status.label}
        </span>
      </div>

      {errorMessage ? (
        <MessageBox
          type="error"
          title="Database status could not be checked"
          message={errorMessage}
        />
      ) : (
        <MessageBox
          type={isReady ? "success" : "info"}
          title={status.label}
          message={status.message}
        />
      )}

      <div className="runtime-readiness-actions">
        <button
          className="secondary-button"
          onClick={onRefresh}
          disabled={isLoading}
          type="button"
        >
          {isLoading ? "Checking..." : "Refresh Database Status"}
        </button>

        <span className="muted">
          Last checked: {lastCheckedAt ? lastCheckedAt.toLocaleString("en-US") : "Not checked yet"}
        </span>
      </div>

      <div className="database-readiness-grid">
        <DatabaseMetricCard
          label="Database Status"
          value={status.label}
          badgeClass={status.badgeClass}
          badgeLabel={status.label}
          helper="Overall persistence health."
        />

        <DatabaseMetricCard
          label="Engine"
          value={engineLabel}
          helper="Storage engine used by the platform."
        />

        <DatabaseMetricCard
          label="Connection"
          value={connectionLabel}
          badgeClass={isReady ? "pass" : "fail"}
          badgeLabel={connectionLabel}
          helper="Application connectivity status."
        />

        <DatabaseMetricCard
          label="Persistence Layer"
          value={isReady ? "Active" : "Unavailable"}
          badgeClass={isReady ? "pass" : "fail"}
          badgeLabel={isReady ? "Active" : "Issue"}
          helper="Required for history and analytics."
        />
      </div>

      <div className="readiness-diagnostics-toggle-row">
        <button
          className="secondary-button compact-button"
          onClick={() => setShowDiagnostics((current) => !current)}
          type="button"
        >
          {showDiagnostics ? "Hide Diagnostics" : "Show Diagnostics"}
        </button>

        <span className="muted">
          Diagnostics are hidden by default.
        </span>
      </div>

      {showDiagnostics && (
        <div className="readiness-diagnostics-panel">
          <div className="database-detail-grid">
            <DiagnosticRow label="Reported Message" value={readiness?.message} />
            <DiagnosticRow label="Connection String" value={maskDatabaseUrl(readiness?.database_url)} />
            <DiagnosticRow label="Reported Error" value={reportedError || "None"} />
          </div>
        </div>
      )}
    </section>
  );
}

export default DatabaseReadinessCard;
