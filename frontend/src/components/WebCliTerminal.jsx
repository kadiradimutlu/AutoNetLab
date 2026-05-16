import { useEffect, useMemo, useRef, useState } from "react";
import MessageBox from "./MessageBox";
import {
  getAuthToken,
  getErrorDetails,
  getErrorMessage,
  getWebCliDeviceReadiness,
  getWebCliUrl
} from "../services/apiService";

const READABLE_WEB_CLI_ERRORS = {
  WEB_CLI_AUTH_REQUIRED: "Authentication is required before opening Web CLI.",
  WEB_CLI_INVALID_TOKEN: "Your login token is invalid. Please log out and sign in again.",
  WEB_CLI_FORBIDDEN: "This user is not allowed to access the selected lab device.",
  WEB_CLI_SESSION_NOT_FOUND: "The selected lab session could not be found.",
  WEB_CLI_DEVICE_NOT_FOUND: "The selected device is not available for this lab session.",
  LAB_NOT_DEPLOYED_FOR_WEB_CLI: "Deploy the lab before opening Web CLI.",
  WEB_CLI_CONTAINER_METADATA_MISSING: "Container metadata is missing for the selected device.",
  DOCKER_NOT_FOUND_FOR_WEB_CLI: "Docker is not available for Web CLI on the backend host.",
  DOCKER_PERMISSION_DENIED_FOR_WEB_CLI: "The backend does not have permission to access Docker for Web CLI.",
  WEB_CLI_CONTAINER_CHECK_TIMEOUT: "The backend timed out while checking the selected device container.",
  WEB_CLI_CONTAINER_CHECK_FAILED: "The backend could not check the selected device container.",
  WEB_CLI_CONTAINER_NOT_RUNNING: "The selected device container is not running.",
  WEB_CLI_PROCESS_START_FAILED: "The backend could not start the Web CLI runtime process."
};

function getDeviceId(device, index) {
  return (
    device.deviceId ||
    device.device_id ||
    device.device ||
    device.deviceName ||
    device.device_name ||
    `device-${index + 1}`
  );
}

function getDeviceLabel(device, index) {
  const deviceId = getDeviceId(device, index);

  return (
    device.deviceName ||
    device.device_name ||
    device.name ||
    deviceId
  );
}

function getReadableWebCliError(errorCode, fallbackMessage = "") {
  return (
    READABLE_WEB_CLI_ERRORS[errorCode] ||
    fallbackMessage ||
    "Web CLI is not ready for the selected device."
  );
}

function parseWebCliMessage(rawMessage) {
  if (!rawMessage) {
    return {
      kind: "output",
      text: ""
    };
  }

  try {
    const parsedMessage = JSON.parse(rawMessage);

    if (parsedMessage?.type === "error") {
      const friendlyMessage = getReadableWebCliError(
        parsedMessage.error_code,
        parsedMessage.message
      );

      return {
        kind: "error",
        text: `[${parsedMessage.error_code || "WEB_CLI_ERROR"}] ${friendlyMessage}`,
        data: parsedMessage
      };
    }

    if (parsedMessage?.type === "connected" || parsedMessage?.type === "runtime_started") {
      return {
        kind: "system",
        text: parsedMessage.message || `Web CLI event: ${parsedMessage.type}`,
        data: parsedMessage
      };
    }

    if (parsedMessage?.message) {
      return {
        kind: "system",
        text: parsedMessage.message,
        data: parsedMessage
      };
    }

    return {
      kind: "output",
      text: JSON.stringify(parsedMessage, null, 2),
      data: parsedMessage
    };
  } catch {
    return {
      kind: "output",
      text: rawMessage
    };
  }
}

function getReadinessDevice(readiness) {
  if (!readiness || typeof readiness !== "object") {
    return null;
  }

  if (Array.isArray(readiness.devices) && readiness.devices.length > 0) {
    return readiness.devices[0];
  }

  if (readiness.device && typeof readiness.device === "object") {
    return readiness.device;
  }

  if (readiness.device_id || readiness.container_name || readiness.container_running !== undefined) {
    return readiness;
  }

  return null;
}

function formatReadinessMessage(readiness) {
  if (!readiness) {
    return "Readiness has not been checked yet.";
  }

  const device = getReadinessDevice(readiness);
  const errorCode = device?.error_code || readiness.error_code;

  if (readiness.lab_deployed === false) {
    return getReadableWebCliError("LAB_NOT_DEPLOYED_FOR_WEB_CLI");
  }

  if (device?.ready === false || readiness.ready === false) {
    return getReadableWebCliError(
      errorCode,
      device?.message || readiness.message || "Selected device is not ready for Web CLI."
    );
  }

  if (readiness.ready === true || device?.ready === true) {
    return readiness.message || device?.message || "Selected device is ready for Web CLI.";
  }

  return readiness.message || device?.message || "Readiness state is unknown.";
}

function ReadinessDetails({ readiness }) {
  if (!readiness) {
    return (
      <div className="web-cli-readiness-card neutral">
        <strong>Readiness</strong>
        <p>Readiness has not been checked yet.</p>
      </div>
    );
  }

  const device = getReadinessDevice(readiness);
  const isReady = readiness.ready === true || device?.ready === true;
  const statusClass = isReady ? "ready" : "not-ready";

  return (
    <div className={`web-cli-readiness-card ${statusClass}`}>
      <div className="result-title-row">
        <div>
          <strong>{isReady ? "Device ready" : "Device not ready"}</strong>
          <p>{formatReadinessMessage(readiness)}</p>
        </div>

        <span className={`badge ${isReady ? "pass" : "fail"}`}>
          {isReady ? "READY" : "NOT READY"}
        </span>
      </div>

      <div className="web-cli-readiness-grid">
        <div>
          <span>Lab Status</span>
          <strong>{readiness.lab_status || "-"}</strong>
        </div>

        <div>
          <span>Lab Deployed</span>
          <strong>{readiness.lab_deployed === true ? "Yes" : readiness.lab_deployed === false ? "No" : "-"}</strong>
        </div>

        <div>
          <span>Current Mode</span>
          <strong>{readiness.current_mode || "-"}</strong>
        </div>

        <div>
          <span>Device</span>
          <strong>{device?.device_id || readiness.device_id || "-"}</strong>
        </div>

        <div>
          <span>Docker Available</span>
          <strong>{device?.docker_available === true ? "Yes" : device?.docker_available === false ? "No" : "-"}</strong>
        </div>

        <div>
          <span>Container Running</span>
          <strong>{device?.container_running === true ? "Yes" : device?.container_running === false ? "No" : "-"}</strong>
        </div>

        <div>
          <span>Error Code</span>
          <strong>{device?.error_code || readiness.error_code || "-"}</strong>
        </div>

        <div>
          <span>Container Name</span>
          <strong>{device?.container_name || "-"}</strong>
        </div>
      </div>
    </div>
  );
}

function WebCliTerminal({
  sessionId,
  devices = [],
  mode = "browser_cli_mvp"
}) {
  const socketRef = useRef(null);
  const outputEndRef = useRef(null);

  const normalizedDevices = useMemo(() => {
    return devices
      .map((device, index) => ({
        ...device,
        deviceId: getDeviceId(device, index),
        label: getDeviceLabel(device, index)
      }))
      .filter((device) => Boolean(device.deviceId));
  }, [devices]);

  const [selectedDeviceId, setSelectedDeviceId] = useState("");
  const [connectionState, setConnectionState] = useState("idle");
  const [command, setCommand] = useState("");
  const [terminalLines, setTerminalLines] = useState([
    {
      kind: "system",
      text: "Web CLI is ready. Select a device and check readiness before connecting."
    }
  ]);
  const [webCliError, setWebCliError] = useState("");
  const [webCliErrorDetails, setWebCliErrorDetails] = useState("");
  const [readiness, setReadiness] = useState(null);

  useEffect(() => {
    if (!selectedDeviceId && normalizedDevices.length > 0) {
      setSelectedDeviceId(normalizedDevices[0].deviceId);
    }
  }, [normalizedDevices, selectedDeviceId]);

  useEffect(() => {
    outputEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [terminalLines]);

  useEffect(() => {
    if (!sessionId || !selectedDeviceId) {
      setReadiness(null);
      setConnectionState("idle");
      return;
    }

    const timeoutId = window.setTimeout(() => {
      checkReadiness({
        silent: true
      });
    }, 250);

    return () => window.clearTimeout(timeoutId);
  }, [sessionId, selectedDeviceId]);

  useEffect(() => {
    return () => {
      disconnectWebCli();
    };
  }, []);

  function appendTerminalLine(kind, text) {
    setTerminalLines((currentLines) => [
      ...currentLines,
      {
        kind,
        text,
        timestamp: new Date().toISOString()
      }
    ]);
  }

  function disconnectWebCli() {
    if (socketRef.current) {
      socketRef.current.close();
      socketRef.current = null;
    }

    setConnectionState("disconnected");
  }

  function normalizeReadinessPayload(payload) {
    const safePayload = payload && typeof payload === "object" ? payload : {};
    const device = getReadinessDevice(safePayload);

    return {
      ...safePayload,
      ready: safePayload.ready === true || device?.ready === true,
      devices: Array.isArray(safePayload.devices)
        ? safePayload.devices
        : device
          ? [device]
          : []
    };
  }

  function setReadinessFailureFromError(error) {
    const data = error?.data && typeof error.data === "object" ? error.data : {};
    const normalizedReadiness = normalizeReadinessPayload({
      success: false,
      session_id: sessionId,
      lab_deployed: data.lab_deployed,
      ready: false,
      error_code: data.error_code || data.detail?.error_code,
      message:
        data.message ||
        data.detail?.message ||
        error.technicalMessage ||
        error.message ||
        "Readiness check failed."
    });

    setReadiness(normalizedReadiness);

    const message = formatReadinessMessage(normalizedReadiness);
    setWebCliError(message);
    setWebCliErrorDetails(getErrorDetails(error));
    setConnectionState("error");
    appendTerminalLine("error", message);
  }

  async function checkReadiness({ silent = false } = {}) {
    setWebCliError("");
    setWebCliErrorDetails("");

    if (!sessionId) {
      const message = "A lab session is required before checking Web CLI readiness.";
      setWebCliError(message);
      setConnectionState("error");
      return null;
    }

    if (!selectedDeviceId) {
      const message = "Select a device before checking Web CLI readiness.";
      setWebCliError(message);
      setConnectionState("error");
      return null;
    }

    if (!getAuthToken()) {
      const message = "A login token is required before checking Web CLI readiness.";
      setWebCliError(message);
      setConnectionState("error");
      return null;
    }

    setConnectionState("checking readiness");

    if (!silent) {
      appendTerminalLine("system", `Checking Web CLI readiness for ${selectedDeviceId}...`);
    }

    try {
      const result = await getWebCliDeviceReadiness(sessionId, selectedDeviceId);
      const normalizedReadiness = normalizeReadinessPayload(result);
      const message = formatReadinessMessage(normalizedReadiness);

      setReadiness(normalizedReadiness);

      if (normalizedReadiness.ready) {
        setConnectionState("ready");

        if (!silent) {
          appendTerminalLine("system", message);
        }

        return normalizedReadiness;
      }

      setConnectionState("error");
      setWebCliError(message);

      if (!silent) {
        appendTerminalLine("error", message);
      }

      return normalizedReadiness;
    } catch (error) {
      setReadinessFailureFromError(error);
      return null;
    }
  }

  async function connectWebCli() {
    setWebCliError("");
    setWebCliErrorDetails("");

    const readinessResult = await checkReadiness({
      silent: false
    });

    if (!readinessResult?.ready) {
      return;
    }

    try {
      const webCliUrl = getWebCliUrl({
        sessionId,
        deviceId: selectedDeviceId
      });

      disconnectWebCli();
      appendTerminalLine("system", `Connecting to ${selectedDeviceId}...`);

      const socket = new WebSocket(webCliUrl);
      socketRef.current = socket;
      setConnectionState("connecting");

      socket.onopen = () => {
        setConnectionState("connected");
        appendTerminalLine("system", "WebSocket connection opened.");
      };

      socket.onmessage = (event) => {
        const parsedMessage = parseWebCliMessage(event.data);
        appendTerminalLine(parsedMessage.kind, parsedMessage.text);

        if (parsedMessage.kind === "error") {
          setWebCliError(parsedMessage.text);
          setConnectionState("error");
        }
      };

      socket.onerror = () => {
        setConnectionState("error");
        setWebCliError("Web CLI connection failed. Check backend, lab deployment, and Docker runtime.");
        appendTerminalLine("error", "WebSocket connection error.");
      };

      socket.onclose = () => {
        setConnectionState("disconnected");
        appendTerminalLine("system", "WebSocket connection closed.");
      };
    } catch (error) {
      setConnectionState("error");
      setWebCliError(getErrorMessage(error, "Web CLI could not be opened."));
      setWebCliErrorDetails(getErrorDetails(error));
      appendTerminalLine("error", error.message || "Web CLI could not be opened.");
    }
  }

  function sendCommand(event) {
    event.preventDefault();

    if (!command.trim()) {
      return;
    }

    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
      setWebCliError("Web CLI is not connected. Connect before sending commands.");
      return;
    }

    const commandToSend = `${command}\n`;
    socketRef.current.send(commandToSend);
    appendTerminalLine("command", `$ ${command}`);
    setCommand("");
  }

  const isCheckingReadiness = connectionState === "checking readiness";
  const isReady = connectionState === "ready";
  const isConnected = connectionState === "connected";
  const isConnecting = connectionState === "connecting";
  const canConnect = isReady && normalizedDevices.length > 0;
  const selectedDevice =
    normalizedDevices.find((device) => device.deviceId === selectedDeviceId) ||
    null;
  const statusBadgeClass = isConnected || isReady ? "pass" : connectionState === "error" ? "fail" : "neutral";

  return (
    <section className="web-cli-panel web-cli-panel-terminal-first">
      <div className="section-title-row">
        <div>
          <h4>Browser Web CLI</h4>
          <p className="muted">
            Open a controlled terminal session for the selected lab device after runtime readiness passes.
          </p>
        </div>

        <span className={`badge ${statusBadgeClass}`}>
          {connectionState}
        </span>
      </div>

      <div className="web-cli-terminal" role="log" aria-label="Web CLI terminal output">
        {terminalLines.map((line, index) => (
          <pre className={`web-cli-line ${line.kind}`} key={`${line.kind}-${index}`}>
            {line.text}
          </pre>
        ))}
        <div ref={outputEndRef} />
      </div>

      <form className="web-cli-command-form" onSubmit={sendCommand}>
        <span>$</span>
        <input
          value={command}
          onChange={(event) => setCommand(event.target.value)}
          disabled={!isConnected}
          placeholder={isConnected ? "Type a command and press Enter" : "Connect Web CLI before sending commands"}
          autoComplete="off"
        />
        <button className="primary-button" disabled={!isConnected || !command.trim()}>
          Send
        </button>
      </form>

      <div className="web-cli-selected-device">
        <div>
          <span>Selected Device</span>
          <strong>{selectedDevice?.label || selectedDeviceId || "No device selected"}</strong>
        </div>

        <div>
          <span>Device ID</span>
          <strong>{selectedDevice?.deviceId || selectedDeviceId || "-"}</strong>
        </div>

        <div>
          <span>Connection State</span>
          <strong>{connectionState}</strong>
        </div>
      </div>

      <div className="web-cli-controls">
        <div className="form-group">
          <label htmlFor="web-cli-device">Device</label>
          <select
            id="web-cli-device"
            value={selectedDeviceId}
            onChange={(event) => {
              setSelectedDeviceId(event.target.value);
              setReadiness(null);
              setWebCliError("");
              setWebCliErrorDetails("");
              setConnectionState("idle");
            }}
            disabled={isConnected || isConnecting || isCheckingReadiness}
          >
            {normalizedDevices.length === 0 && (
              <option value="">No devices available</option>
            )}

            {normalizedDevices.map((device) => (
              <option value={device.deviceId} key={device.deviceId}>
                {device.label} ({device.deviceId})
              </option>
            ))}
          </select>
        </div>

        <div className="web-cli-button-row">
          <button
            className="secondary-button"
            onClick={() => checkReadiness({ silent: false })}
            disabled={isConnected || isConnecting || isCheckingReadiness || normalizedDevices.length === 0}
            type="button"
          >
            {isCheckingReadiness ? "Checking..." : "Check Readiness"}
          </button>

          <button
            className="primary-button"
            onClick={connectWebCli}
            disabled={!canConnect || isConnected || isConnecting || isCheckingReadiness}
            title={!canConnect ? "Check readiness and deploy the lab before connecting." : "Connect to the selected device."}
            type="button"
          >
            {isConnecting ? "Connecting..." : canConnect ? "Connect Web CLI" : "Not Ready"}
          </button>

          <button
            className="secondary-button"
            onClick={disconnectWebCli}
            disabled={!isConnected && !isConnecting}
            type="button"
          >
            Disconnect
          </button>
        </div>
      </div>

      {webCliError && (
        <>
          <MessageBox
            type="error"
            title="Web CLI readiness"
            message={webCliError}
          />

          {webCliErrorDetails && (
            <div className="technical-detail-box">
              <strong>Technical detail</strong>
              <p>{webCliErrorDetails}</p>
            </div>
          )}
        </>
      )}

      <ReadinessDetails readiness={readiness} />

      <div className="web-cli-help-stack">
        <MessageBox
          type="info"
          title="Safe Web CLI access"
          message="Device selection uses trusted backend lab metadata. Container names cannot be typed or overridden from the browser."
        />

        <p className="footer-note">
          Current mode: {mode || "browser_cli_mvp"}. Local Docker Exec commands remain available below as a fallback.
        </p>
      </div>
    </section>
  );
}

export default WebCliTerminal;
