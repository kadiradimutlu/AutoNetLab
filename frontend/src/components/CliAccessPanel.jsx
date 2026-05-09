import MessageBox from "./MessageBox";
import DeviceCliCard from "./DeviceCliCard";

function getModeLabel(mode) {
  const normalizedMode = String(mode || "").toLowerCase();

  if (normalizedMode === "local_docker_exec_demo" || normalizedMode === "docker_exec") {
    return "Local Docker Exec Demo Mode";
  }

  if (normalizedMode.includes("ssh")) {
    return "SSH Gateway";
  }

  if (normalizedMode.includes("browser")) {
    return "Browser CLI";
  }

  return "CLI Access Mode";
}

function getModeDescription(mode) {
  const normalizedMode = String(mode || "").toLowerCase();

  if (normalizedMode === "local_docker_exec_demo" || normalizedMode === "docker_exec") {
    return "This build uses local terminal commands with docker exec. Open a terminal on the machine running Docker and Containerlab, then copy the command for the target device.";
  }

  return "This panel only shows access methods provided by the backend. Browser-based CLI and SSH Gateway are not shown unless the backend provides them.";
}

function CliAccessPanel({
  cliAccess = [],
  mode = "local_docker_exec_demo",
  warning = "",
  details = "",
  copyNotice = "",
  copiedCommandKey = "",
  onCopyCommand
}) {
  return (
    <section className="cli-access-panel">
      <div className="section-title-row">
        <div>
          <h4>CLI Access</h4>
          <p className="muted">
            Access the lab devices from your terminal and troubleshoot the network state manually.
          </p>
        </div>

        <span className="badge neutral">{getModeLabel(mode)}</span>
      </div>

      <div className="cli-mode-note">
        <strong>{getModeLabel(mode)}</strong>
        <p>{getModeDescription(mode)}</p>
        <p>
          Browser-based CLI and SSH Gateway are documented as future work and are not enabled in this frontend build.
        </p>
      </div>

      <MessageBox
        type="info"
        title="Student-safe CLI guidance"
        message="This panel provides access commands only. It does not reveal injected errors, expected fixes, or solution details."
      />

      {warning && (
        <>
          <MessageBox
            type="error"
            title="CLI access warning"
            message={warning}
          />

          {details && (
            <div className="technical-detail-box">
              <strong>Technical detail</strong>
              <p>{details}</p>
            </div>
          )}
        </>
      )}

      {copyNotice && (
        <MessageBox
          type="info"
          title="Copy successful"
          message={copyNotice}
        />
      )}

      <div className="result-list">
        {cliAccess.length === 0 && (
          <p className="muted">CLI access information is not available yet.</p>
        )}

        {cliAccess.map((cli, index) => (
          <DeviceCliCard
            cli={cli}
            index={index}
            key={`${cli.deviceName || cli.device_name || "device"}-${index}`}
            copiedCommandKey={copiedCommandKey}
            onCopyCommand={onCopyCommand}
          />
        ))}
      </div>
    </section>
  );
}

export default CliAccessPanel;
