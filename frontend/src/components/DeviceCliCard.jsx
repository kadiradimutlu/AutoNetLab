
function getSafeText(value, fallback = "-") {
  if (value === undefined || value === null || value === "") {
    return fallback;
  }

  return String(value);
}

function getAccessMethodLabel(method) {
  const normalizedMethod = String(method || "").toLowerCase();

  if (normalizedMethod === "local_docker_exec_demo" || normalizedMethod === "docker_exec") {
    return "Local Docker Exec Demo Mode";
  }

  if (normalizedMethod.includes("ssh")) {
    return "SSH Gateway";
  }

  if (normalizedMethod.includes("browser")) {
    return "Browser CLI";
  }

  return getSafeText(method, "CLI Access");
}


function getReadableDeviceName(cli, fallbackName) {
  const rawDeviceId = String(cli.deviceId || cli.device_id || "").trim();
  const rawName = String(cli.deviceName || cli.device_name || "").trim();
  const dockerCommand = String(cli.dockerExecCommand || cli.docker_exec_command || cli.command || "").toLowerCase();
  const normalizedDeviceId = rawDeviceId || rawName || fallbackName || "Device";

  if (
    normalizedDeviceId.toLowerCase().includes("srl") ||
    rawName.toLowerCase().includes("sr linux") ||
    dockerCommand.includes("sr_cli")
  ) {
    return `${normalizedDeviceId} — SR Linux CLI`;
  }

  if (
    normalizedDeviceId.toLowerCase().includes("client") ||
    rawName.toLowerCase().includes("linux shell") ||
    dockerCommand.endsWith(" sh") ||
    dockerCommand.includes(" sh ")
  ) {
    return `${normalizedDeviceId} — Linux Shell`;
  }

  return rawName || normalizedDeviceId;
}

function DeviceCliCard({
  cli,
  index,
  copiedCommandKey,
  onCopyCommand
}) {
  const containerName = getSafeText(cli.containerName || cli.container_name);
  const accessMethod = getSafeText(cli.accessMethod || cli.access_method, "local_docker_exec_demo");
  const dockerCommand = cli.dockerExecCommand || cli.docker_exec_command || cli.command || "";
  const deviceName = getReadableDeviceName(cli, `Device ${index + 1}`);
  const sshCommand = cli.sshCommand || cli.ssh_command || "";
  const description = cli.description || `Use the command below to access ${deviceName} from your local terminal.`;

  const dockerCommandKey = `${deviceName}-docker-${index}`;
  const sshCommandKey = `${deviceName}-ssh-${index}`;

  return (
    <div className="list-item cli-card">
      <div className="result-title-row">
        <div>
          <strong>{deviceName}</strong>
          <p className="muted">{description}</p>
        </div>

        <span className="badge neutral">CLI</span>
      </div>

      <div className="cli-meta-grid">
        <div>
          <span className="muted">Container Name</span>
          <strong>{containerName}</strong>
        </div>

        <div>
          <span className="muted">Access Method</span>
          <strong>{getAccessMethodLabel(accessMethod)}</strong>
        </div>
      </div>

      {dockerCommand && (
        <div className="command-section">
          <p className="muted">Docker Exec Command</p>

          <div className="command-row">
            <code className="command-box">{dockerCommand}</code>

            <button
              className="secondary-button"
              onClick={() => onCopyCommand(dockerCommand, dockerCommandKey)}
            >
              {copiedCommandKey === dockerCommandKey ? "Copied" : "Copy"}
            </button>
          </div>
        </div>
      )}

      {sshCommand && (
        <div className="command-section">
          <p className="muted">SSH Command</p>

          <div className="command-row">
            <code className="command-box">{sshCommand}</code>

            <button
              className="secondary-button"
              onClick={() => onCopyCommand(sshCommand, sshCommandKey)}
            >
              {copiedCommandKey === sshCommandKey ? "Copied" : "Copy"}
            </button>
          </div>
        </div>
      )}

      {!dockerCommand && !sshCommand && (
        <p className="muted">
          No executable CLI command is available for this device yet.
        </p>
      )}
    </div>
  );
}

export default DeviceCliCard;

