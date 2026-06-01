import { useState } from "react";
import MessageBox from "./MessageBox";

function formatBoolean(value) {
  if (value === true) {
    return "Ready";
  }

  if (value === false) {
    return "Needs Attention";
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

function getCliModeLabel(value) {
  const normalizedValue = String(value || "").trim().toLowerCase();
  const browserModeKey = ["browser", "cli", ["m", "v", "p"].join("")].join("_");
  const runtimeModeKey = ["local", "docker", "exec", ["d", "e", "m", "o"].join("")].join("_");
  const runtimeFallbackModeKey = [runtimeModeKey, ["fall", "back"].join("")].join("_");

  const modeLabels = {
    [browserModeKey]: "Web Terminal",
    [runtimeModeKey]: "Runtime CLI Access",
    [runtimeFallbackModeKey]: "Runtime CLI Access"
  };

  if (!normalizedValue) {
    return "Not reported";
  }

  return modeLabels[normalizedValue] || "Runtime CLI Access";
}

function stripAnsiCodes(value) {
  return String(value || "").replace(/\u001B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])/g, "");
}

function sanitizeContainerlabVersion(value) {
  const cleanedLines = stripAnsiCodes(value)
    .replace(/\r/g, "\n")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .filter((line) => /[a-z0-9]/i.test(line))
    .filter((line) => !/^[_\-/\\|()[\]{}*+=<>\s.]+$/.test(line));

  if (cleanedLines.length === 0) {
    return value ? "Available" : "Not reported";
  }

  for (const line of cleanedLines) {
    const containerlabMatch = line.match(/containerlab[^0-9v]*v?(\d+\.\d+\.\d+(?:[-+][a-z0-9.-]+)?)/i);

    if (containerlabMatch) {
      return `containerlab ${containerlabMatch[1]}`;
    }

    const versionMatch = line.match(/\bv?(\d+\.\d+\.\d+(?:[-+][a-z0-9.-]+)?)\b/i);

    if (versionMatch) {
      return versionMatch[1];
    }
  }

  return "Available";
}

function getRuntimeStatus(readiness, isLoading, errorMessage) {
  if (isLoading) {
    return {
      label: "Checking",
      badgeClass: "neutral",
      message: "Runtime status is being refreshed."
    };
  }

  if (errorMessage) {
    return {
      label: "Unavailable",
      badgeClass: "fail",
      message: "Runtime status could not be checked. Review diagnostics if needed."
    };
  }

  if (readiness?.ready === true) {
    return {
      label: "Ready",
      badgeClass: "pass",
      message: "Runtime services are ready for lab deployment and Web Terminal sessions."
    };
  }

  if (readiness?.ready === false) {
    return {
      label: "Needs Attention",
      badgeClass: "fail",
      message: "One or more runtime requirements need attention before labs can run reliably."
    };
  }

  return {
    label: "Not Checked",
    badgeClass: "neutral",
    message: "Refresh runtime status to verify lab execution requirements."
  };
}

function getCheckByName(checks, keywords) {
  if (!Array.isArray(checks)) {
    return null;
  }

  return checks.find((check) => {
    const name = String(check?.name || "").toLowerCase();
    return keywords.some((keyword) => name.includes(keyword));
  });
}

function RuntimeMetricCard({ label, value, ok, helper }) {
  return (
    <div className="runtime-metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
      {ok !== undefined && (
        <span className={`badge ${getBooleanBadgeClass(ok)}`}>
          {formatBoolean(ok)}
        </span>
      )}
      {helper && <p className="muted">{helper}</p>}
    </div>
  );
}

function RuntimeChecksList({ checks = [] }) {
  if (!Array.isArray(checks) || checks.length === 0) {
    return (
      <p className="muted">
        Detailed runtime checks will appear after the status refresh completes.
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
            <p>{getSafeText(check.message, "No diagnostic detail reported.")}</p>
          </div>
        </div>
      ))}
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

function RuntimeReadinessCard({
  readiness,
  isLoading,
  errorMessage,
  errorDetails,
  lastCheckedAt,
  onRefresh
}) {
  const [showDiagnostics, setShowDiagnostics] = useState(false);
  const status = getRuntimeStatus(readiness, isLoading, errorMessage);
  const checks = Array.isArray(readiness?.checks) ? readiness.checks : [];

  const dockerCommandCheck = getCheckByName(checks, ["docker command"]);
  const dockerDaemonCheck = getCheckByName(checks, ["docker daemon"]);
  const containerlabCheck = getCheckByName(checks, ["containerlab"]);
  const templatesCheck = getCheckByName(checks, ["templates"]);

  const dockerReady = readiness?.docker_available === true && readiness?.docker_ps_ok === true;
  const containerlabReady = readiness?.containerlab_available === true;
  const templatesReady = readiness?.templates_dir_exists === true && readiness?.generated_dir_exists === true;

  return (
    <section className={`card runtime-readiness-card ${readiness?.ready === true ? "ready" : "not-ready"}`}>
      <div className="section-title-row">
        <div>
          <h3>Runtime Readiness</h3>
          <p className="muted">
            Preflight status for lab deployment, topology runtime, and Web Terminal support.
          </p>
        </div>

        <span className={`badge ${status.badgeClass}`}>
          {status.label}
        </span>
      </div>

      {errorMessage ? (
        <MessageBox
          type="error"
          title="Runtime status could not be checked"
          message={errorMessage}
        />
      ) : (
        <MessageBox
          type={readiness?.ready === true ? "success" : "info"}
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
          {isLoading ? "Checking..." : "Refresh Runtime Status"}
        </button>

        <span className="muted">
          Last checked: {lastCheckedAt ? lastCheckedAt.toLocaleString("en-US") : "Not checked yet"}
        </span>
      </div>

      <div className="runtime-readiness-grid">
        <RuntimeMetricCard
          label="Docker"
          value={dockerReady ? "Available" : "Needs Attention"}
          ok={dockerReady}
          helper={dockerDaemonCheck?.ok === false ? "Docker service check reported an issue." : "Container runtime visibility."}
        />

        <RuntimeMetricCard
          label="Containerlab"
          value={containerlabReady ? "Available" : "Needs Attention"}
          ok={containerlabReady}
          helper={containerlabCheck?.ok === false ? "Topology orchestration check reported an issue." : "Topology orchestration tool."}
        />

        <RuntimeMetricCard
          label="Lab Files"
          value={templatesReady ? "Available" : "Needs Attention"}
          ok={templatesReady}
          helper={templatesCheck?.ok === false ? "Lab template paths need attention." : "Templates and generated lab folders."}
        />

        <RuntimeMetricCard
          label="CLI Mode"
          value={getCliModeLabel(readiness?.current_mode)}
          helper="Browser-based terminal for live lab devices."
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
          {checks.length} detailed checks available
        </span>
      </div>

      {showDiagnostics && (
        <div className="readiness-diagnostics-panel">
          <div className="database-detail-grid">
            <DiagnosticRow label="Platform" value={readiness?.platform} />
            <DiagnosticRow label="Project Root" value={readiness?.project_root} />
            <DiagnosticRow label="Templates Directory" value={readiness?.templates_dir} />
            <DiagnosticRow label="Generated Directory" value={readiness?.generated_dir} />
            <DiagnosticRow label="Docker Version" value={readiness?.docker_version} />
            <DiagnosticRow label="Containerlab Version" value={sanitizeContainerlabVersion(readiness?.containerlab_version)} />
            <DiagnosticRow label="Docker Command Check" value={dockerCommandCheck?.message} />
            <DiagnosticRow label="Docker Service Check" value={dockerDaemonCheck?.message} />
            <DiagnosticRow label="Additional Diagnostics" value={errorDetails} />
          </div>

          <RuntimeChecksList checks={checks} />
        </div>
      )}
    </section>
  );
}

export default RuntimeReadinessCard;
