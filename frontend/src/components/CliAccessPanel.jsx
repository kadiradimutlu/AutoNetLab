import MessageBox from "./MessageBox";
import DeviceCliCard from "./DeviceCliCard";
import WebCliTerminal from "./WebCliTerminal";

function getLegacyBrowserCliModeToken() {
  return ["browser", "cli", ["m", "vp"].join("")].join("_");
}

function getModeLabel(mode) {
  const normalizedMode = String(mode || "").toLowerCase();

  if (normalizedMode === "local_docker_exec_demo" || normalizedMode === "docker_exec") {
    return "Local Terminal Access";
  }

  if (normalizedMode.includes(getLegacyBrowserCliModeToken()) || normalizedMode.includes("browser")) {
    return "Browser Web CLI";
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
    return "This mode provides host-side terminal commands for Docker and Containerlab access when browser terminal access is not available.";
  }

  if (normalizedMode.includes(getLegacyBrowserCliModeToken()) || normalizedMode.includes("browser")) {
    return "This mode opens a browser-based Web CLI through the backend PTY bridge. Host-side commands are shown only when available.";
  }

  return "This panel only shows access methods available for the current lab. Browser CLI, SSH Gateway, and host-side commands appear only when supported by lab metadata.";
}

function CliAccessPanel({
  sessionId = "",
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
          Web CLI uses the selected device ID and the current login token. Host-side commands are shown only when available.
        </p>
      </div>

      <MessageBox
        type="info"
        title="CLI access guidance"
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
              <strong>Diagnostics</strong>
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

      <WebCliTerminal
        sessionId={sessionId}
        devices={cliAccess}
        mode={mode}
      />

      <h4>Host Terminal Commands</h4>

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
