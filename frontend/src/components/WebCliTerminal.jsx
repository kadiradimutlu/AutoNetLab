import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import "@xterm/xterm/css/xterm.css";
import MessageBox from "./MessageBox";
import {
  getAuthToken,
  getErrorDetails,
  getErrorMessage,
  getWebCliDeviceReadiness,
  getWebTerminalUrl
} from "../services/apiService";

const READABLE_WEB_CLI_ERRORS = {
  WEB_CLI_AUTH_REQUIRED: "Authentication is required before opening Web Terminal.",
  WEB_CLI_INVALID_TOKEN: "Your login token is invalid. Please log out and sign in again.",
  WEB_CLI_FORBIDDEN: "This user is not allowed to access the selected lab device.",
  WEB_CLI_SESSION_NOT_FOUND: "The selected lab session could not be found.",
  WEB_CLI_DEVICE_NOT_FOUND: "The selected device is not available for this lab session.",
  LAB_NOT_DEPLOYED_FOR_WEB_CLI: "Deploy the lab before opening Web Terminal.",
  WEB_CLI_CONTAINER_METADATA_MISSING: "Container metadata is missing for the selected device.",
  DOCKER_NOT_FOUND_FOR_WEB_CLI: "Docker is not available for Web Terminal on the application host.",
  DOCKER_PERMISSION_DENIED_FOR_WEB_CLI: "The application service does not have permission to access Docker for Web Terminal.",
  WEB_CLI_CONTAINER_CHECK_TIMEOUT: "The application service timed out while checking the selected device container.",
  WEB_CLI_CONTAINER_CHECK_FAILED: "The application service could not check the selected device container.",
  WEB_CLI_CONTAINER_NOT_RUNNING: "The selected device container is not running.",
  WEB_CLI_PROCESS_START_FAILED: "The application service could not start the Web Terminal runtime process."
};

const CONTROL_FRAME_TYPES = new Set([
  "terminal_connected",
  "terminal_started",
  "connected",
  "runtime_started"
]);

const TERMINAL_ENCODER = new TextEncoder();
const TERMINAL_DECODER = new TextDecoder();

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
    "Web Terminal is not ready for the selected device."
  );
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
      device?.message || readiness.message || "Selected device is not ready for Web Terminal."
    );
  }

  if (readiness.ready === true || device?.ready === true) {
    return readiness.message || device?.message || "Selected device is ready for Web Terminal.";
  }

  return readiness.message || device?.message || "Readiness state is unknown.";
}

function parseControlFrame(rawMessage) {
  if (!rawMessage || typeof rawMessage !== "string") {
    return null;
  }

  try {
    const parsedMessage = JSON.parse(rawMessage);

    if (!parsedMessage || typeof parsedMessage !== "object") {
      return null;
    }

    if (parsedMessage.type === "error") {
      return {
        kind: "error",
        message: `[${parsedMessage.error_code || "WEB_TERMINAL_ERROR"}] ${getReadableWebCliError(
          parsedMessage.error_code,
          parsedMessage.message
        )}`
      };
    }

    if (CONTROL_FRAME_TYPES.has(parsedMessage.type)) {
      return {
        kind: "system",
        message: parsedMessage.message || `Terminal event: ${parsedMessage.type}`
      };
    }

    if (parsedMessage.message) {
      return {
        kind: "system",
        message: parsedMessage.message
      };
    }

    return null;
  } catch {
    return null;
  }
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

function formatConnectionState(state) {
  return String(state || "idle")
    .split(" ")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function getStatusBadgeClass(state) {
  if (state === "connected" || state === "ready") {
    return "pass";
  }

  if (state === "error") {
    return "fail";
  }

  return "neutral";
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

function TerminalPane({
  active,
  device,
  mode,
  onStatusChange,
  sessionId
}) {
  const deviceId = device?.deviceId || "";
  const deviceLabel = device?.label || deviceId || "Device";
  const socketRef = useRef(null);
  const terminalRef = useRef(null);
  const fitAddonRef = useRef(null);
  const terminalContainerRef = useRef(null);
  const dataDisposableRef = useRef(null);
  const resizeObserverRef = useRef(null);
  const activeRef = useRef(active);

  const [connectionState, setConnectionState] = useState("idle");
  const [webCliError, setWebCliError] = useState("");
  const [webCliErrorDetails, setWebCliErrorDetails] = useState("");
  const [readiness, setReadiness] = useState(null);

  const terminalPanelId = `terminal-panel-${deviceId}`;
  const isCheckingReadiness = connectionState === "checking readiness";
  const isReady = readiness?.ready === true;
  const isConnected = connectionState === "connected";
  const isConnecting = connectionState === "connecting";
  const canConnect = isReady && !isConnected && !isConnecting && !isCheckingReadiness;
  const statusBadgeClass = getStatusBadgeClass(connectionState);

  useEffect(() => {
    activeRef.current = active;

    if (active) {
      window.setTimeout(() => {
        fitTerminal();
        terminalRef.current?.focus();
        sendResizeFrame();
      }, 80);
    }
  }, [active]);

  useEffect(() => {
    onStatusChange(deviceId, connectionState, deviceLabel);
  }, [connectionState, deviceId, deviceLabel, onStatusChange]);

  useEffect(() => {
    if (!terminalContainerRef.current || terminalRef.current) {
      return undefined;
    }

    const terminal = new Terminal({
      cursorBlink: true,
      convertEol: false,
      fontFamily: '"Cascadia Mono", "Consolas", "Menlo", monospace',
      fontSize: 14,
      lineHeight: 1.15,
      rows: 24,
      cols: 100,
      scrollback: 3000,
      theme: {
        background: "#020617",
        foreground: "#e2e8f0",
        cursor: "#93c5fd",
        selectionBackground: "#1d4ed8"
      }
    });
    const fitAddon = new FitAddon();

    terminal.loadAddon(fitAddon);
    terminal.open(terminalContainerRef.current);

    if (activeRef.current) {
      try {
        fitAddon.fit();
      } catch (error) {
        console.warn("Initial xterm fit failed.", error);
      }
    }

    terminal.writeln("AutoNetLab Terminal Workspace");
    terminal.writeln(`Terminal tab: ${deviceLabel} (${deviceId})`);
    terminal.writeln("Check readiness, then connect.");
    terminal.writeln("");

    dataDisposableRef.current = terminal.onData((data) => {
      const socket = socketRef.current;

      if (!socket || socket.readyState !== WebSocket.OPEN) {
        return;
      }

      socket.send(TERMINAL_ENCODER.encode(data));
    });

    terminalRef.current = terminal;
    fitAddonRef.current = fitAddon;

    resizeObserverRef.current = new ResizeObserver(() => {
      if (!activeRef.current) {
        return;
      }

      fitTerminal();
      sendResizeFrame();
    });
    resizeObserverRef.current.observe(terminalContainerRef.current);

    return () => {
      const socket = socketRef.current;

      if (socket) {
        socket.onopen = null;
        socket.onmessage = null;
        socket.onerror = null;
        socket.onclose = null;

        if (
          socket.readyState === WebSocket.OPEN ||
          socket.readyState === WebSocket.CONNECTING
        ) {
          socket.close();
        }
      }

      dataDisposableRef.current?.dispose();
      resizeObserverRef.current?.disconnect();
      terminal.dispose();

      dataDisposableRef.current = null;
      resizeObserverRef.current = null;
      socketRef.current = null;
      terminalRef.current = null;
      fitAddonRef.current = null;
    };
  }, [deviceId, deviceLabel]);

  useEffect(() => {
    if (!active || !sessionId || !deviceId || readiness || connectionState !== "idle") {
      return undefined;
    }

    const timer = window.setTimeout(() => {
      checkReadiness({ silent: true });
    }, 250);

    return () => window.clearTimeout(timer);
  }, [active, connectionState, deviceId, readiness, sessionId]);

  function writeTerminal(text = "") {
    terminalRef.current?.write(text);
  }

  function writeTerminalLine(text = "") {
    terminalRef.current?.writeln(text);
  }

  function clearTerminal() {
    terminalRef.current?.clear();
    writeTerminalLine("AutoNetLab Terminal Workspace");
    writeTerminalLine(`Terminal tab: ${deviceLabel} (${deviceId})`);
    writeTerminalLine("");
  }

  function fitTerminal() {
    try {
      fitAddonRef.current?.fit();
    } catch (error) {
      console.warn("xterm fit failed.", error);
    }
  }

  function sendResizeFrame() {
    const socket = socketRef.current;
    const terminal = terminalRef.current;

    if (!socket || !terminal || socket.readyState !== WebSocket.OPEN) {
      return;
    }

    socket.send(JSON.stringify({
      type: "resize",
      cols: terminal.cols,
      rows: terminal.rows
    }));
  }

  function disconnectWebTerminal({ writeMessage = true } = {}) {
    const socket = socketRef.current;

    if (socket) {
      socket.onopen = null;
      socket.onmessage = null;
      socket.onerror = null;
      socket.onclose = null;

      if (
        socket.readyState === WebSocket.OPEN ||
        socket.readyState === WebSocket.CONNECTING
      ) {
        socket.close();
      }
    }

    socketRef.current = null;
    setConnectionState("disconnected");

    if (writeMessage) {
      writeTerminalLine("\r\n[system] Terminal connection closed.");
    }
  }

  function setReadinessFailureFromError(error) {
    const normalizedReadiness = normalizeReadinessPayload({
      success: false,
      session_id: sessionId,
      lab_deployed: error?.data?.lab_deployed,
      ready: false,
      error_code: error?.data?.error_code || error?.data?.detail?.error_code,
      message:
        error?.data?.message ||
        error?.data?.detail?.message ||
        error?.technicalMessage ||
        error?.message ||
        "Readiness check failed."
    });

    setReadiness(normalizedReadiness);
    const message = formatReadinessMessage(normalizedReadiness);
    setWebCliError(message);
    setWebCliErrorDetails(getErrorDetails(error));
    setConnectionState("error");
    writeTerminalLine(`[error] ${message}`);
  }

  async function checkReadiness({ silent = false } = {}) {
    setWebCliError("");
    setWebCliErrorDetails("");

    if (!sessionId) {
      const message = "A lab session is required before checking Web Terminal readiness.";
      setWebCliError(message);
      setConnectionState("error");
      writeTerminalLine(`[error] ${message}`);
      return null;
    }

    if (!deviceId) {
      const message = "Select a device before checking Web Terminal readiness.";
      setWebCliError(message);
      setConnectionState("error");
      writeTerminalLine(`[error] ${message}`);
      return null;
    }

    if (!getAuthToken()) {
      const message = "A login token is required before checking Web Terminal readiness.";
      setWebCliError(message);
      setConnectionState("error");
      writeTerminalLine(`[error] ${message}`);
      return null;
    }

    setConnectionState("checking readiness");

    if (!silent) {
      writeTerminalLine(`[system] Checking readiness for ${deviceId}...`);
    }

    try {
      const result = await getWebCliDeviceReadiness(sessionId, deviceId);
      const normalizedReadiness = normalizeReadinessPayload(result);
      const message = formatReadinessMessage(normalizedReadiness);

      setReadiness(normalizedReadiness);

      if (normalizedReadiness.ready) {
        setConnectionState("ready");

        if (!silent) {
          writeTerminalLine(`[system] ${message}`);
        }

        return normalizedReadiness;
      }

      setConnectionState("error");
      setWebCliError(message);

      if (!silent) {
        writeTerminalLine(`[error] ${message}`);
      }

      return normalizedReadiness;
    } catch (error) {
      setReadinessFailureFromError(error);
      return null;
    }
  }

  async function connectWebTerminal() {
    setWebCliError("");
    setWebCliErrorDetails("");

    const readinessResult = await checkReadiness({
      silent: false
    });

    if (!readinessResult?.ready) {
      return;
    }

    try {
      const webTerminalUrl = getWebTerminalUrl({
        sessionId,
        deviceId
      });

      disconnectWebTerminal({ writeMessage: false });

      clearTerminal();
      writeTerminalLine(`[system] Connecting to ${deviceId}...`);

      const socket = new WebSocket(webTerminalUrl);
      socket.binaryType = "arraybuffer";
      socketRef.current = socket;
      setConnectionState("connecting");

      socket.onopen = () => {
        setConnectionState("connected");
        writeTerminalLine("[system] WebSocket connection opened.");
        fitTerminal();
        sendResizeFrame();

        if (activeRef.current) {
          terminalRef.current?.focus();
        }
      };

      socket.onmessage = async (event) => {
        if (typeof event.data === "string") {
          const controlFrame = parseControlFrame(event.data);

          if (controlFrame) {
            if (controlFrame.kind === "error") {
              setWebCliError(controlFrame.message);
              setConnectionState("error");
            }

            writeTerminalLine(`[${controlFrame.kind}] ${controlFrame.message}`);
            return;
          }

          writeTerminal(event.data);
          return;
        }

        if (event.data instanceof ArrayBuffer) {
          writeTerminal(TERMINAL_DECODER.decode(event.data));
          return;
        }

        if (event.data instanceof Blob) {
          const buffer = await event.data.arrayBuffer();
          writeTerminal(TERMINAL_DECODER.decode(buffer));
        }
      };

      socket.onerror = () => {
        setConnectionState("error");
        setWebCliError("Web Terminal connection failed. Check lab deployment and Docker runtime.");
        writeTerminalLine("[error] WebSocket connection error.");
      };

      socket.onclose = () => {
        socketRef.current = null;
        setConnectionState("disconnected");
        writeTerminalLine("\r\n[system] WebSocket connection closed.");
      };
    } catch (error) {
      setConnectionState("error");
      setWebCliError(getErrorMessage(error, "Web Terminal could not be opened."));
      setWebCliErrorDetails(getErrorDetails(error));
      writeTerminalLine(`[error] ${error.message || "Web Terminal could not be opened."}`);
    }
  }

  function reconnectWebTerminal() {
    disconnectWebTerminal({ writeMessage: false });
    connectWebTerminal();
  }

  return (
    <div
      className={`terminal-tab-panel ${active ? "active" : "inactive"}`}
      hidden={!active}
      id={terminalPanelId}
      role="tabpanel"
      aria-label={`${deviceLabel} terminal panel`}
    >
      <div className="web-terminal-shell-card">
        <div className="web-terminal-toolbar terminal-workspace-toolbar">
          <div>
            <span className="muted">Active terminal tab</span>
            <strong>{deviceLabel}</strong>
          </div>

          <div className="terminal-workspace-toolbar-badges">
            <span className={`badge ${statusBadgeClass}`}>
              {formatConnectionState(connectionState)}
            </span>

            <span className={`badge ${isConnected ? "pass" : "neutral"}`}>
              {isConnected ? "LIVE PTY" : "NOT LIVE"}
            </span>
          </div>
        </div>

        <div
          className="xterm-shell-container multi-terminal-xterm-container"
          ref={terminalContainerRef}
          onClick={() => terminalRef.current?.focus()}
          role="application"
          aria-label={`Interactive Web Terminal for ${deviceLabel}`}
        />
      </div>

      <div className="web-cli-selected-device terminal-workspace-selected-device">
        <div>
          <span>Selected Device</span>
          <strong>{deviceLabel}</strong>
        </div>

        <div>
          <span>Device ID</span>
          <strong>{deviceId || "-"}</strong>
        </div>

        <div>
          <span>Endpoint</span>
          <strong>/terminal/ws</strong>
        </div>

        <div>
          <span>Connection State</span>
          <strong>{formatConnectionState(connectionState)}</strong>
        </div>
      </div>

      <div className="web-cli-controls terminal-workspace-controls">
        <div className="web-cli-button-row">
          <button
            className="secondary-button"
            onClick={() => checkReadiness({ silent: false })}
            disabled={isConnected || isConnecting || isCheckingReadiness}
            type="button"
          >
            {isCheckingReadiness ? "Checking..." : "Check Readiness"}
          </button>

          <button
            className="primary-button"
            onClick={connectWebTerminal}
            disabled={!canConnect}
            title={!canConnect ? "Check readiness and deploy the lab before connecting." : "Connect to this device."}
            type="button"
          >
            {isConnecting ? "Connecting..." : isConnected ? "Connected" : "Connect Terminal"}
          </button>

          <button
            className="secondary-button"
            onClick={reconnectWebTerminal}
            disabled={isConnecting || isCheckingReadiness}
            type="button"
          >
            Reconnect
          </button>

          <button
            className="secondary-button"
            onClick={() => disconnectWebTerminal()}
            disabled={!isConnected && !isConnecting}
            type="button"
          >
            Disconnect
          </button>

          <button
            className="secondary-button"
            onClick={clearTerminal}
            type="button"
          >
            Clear Terminal
          </button>
        </div>
      </div>

      {webCliError && (
        <>
          <MessageBox
            type="error"
            title="Web Terminal readiness"
            message={webCliError}
          />

          {webCliErrorDetails && (
            <div className="technical-detail-box">
              <strong>Diagnostics</strong>
              <p>{webCliErrorDetails}</p>
            </div>
          )}
        </>
      )}

      <ReadinessDetails readiness={readiness} />

      <p className="footer-note">
        Current mode: {mode || "browser_cli_mvp"}. This tab keeps its own WebSocket, xterm state, and terminal scrollback while you switch devices.
      </p>
    </div>
  );
}

function WebCliTerminal({
  sessionId,
  devices = [],
  mode = "browser_cli_mvp"
}) {
  const [activeDeviceId, setActiveDeviceId] = useState("");
  const [terminalStatuses, setTerminalStatuses] = useState({});

  const normalizedDevices = useMemo(() => {
    return devices
      .map((device, index) => ({
        ...device,
        deviceId: getDeviceId(device, index),
        label: getDeviceLabel(device, index)
      }))
      .filter((device) => Boolean(device.deviceId));
  }, [devices]);

  useEffect(() => {
    if (normalizedDevices.length === 0) {
      setActiveDeviceId("");
      return;
    }

    const activeDeviceStillExists = normalizedDevices.some(
      (device) => device.deviceId === activeDeviceId
    );

    if (!activeDeviceId || !activeDeviceStillExists) {
      setActiveDeviceId(normalizedDevices[0].deviceId);
    }
  }, [activeDeviceId, normalizedDevices]);

  const handleStatusChange = useCallback((deviceId, state, label) => {
    if (!deviceId) {
      return;
    }

    setTerminalStatuses((currentStatuses) => {
      const currentStatus = currentStatuses[deviceId];

      if (
        currentStatus?.state === state &&
        currentStatus?.label === label
      ) {
        return currentStatuses;
      }

      return {
        ...currentStatuses,
        [deviceId]: {
          label,
          state,
          updatedAt: Date.now()
        }
      };
    });
  }, []);

  const activeDevice =
    normalizedDevices.find((device) => device.deviceId === activeDeviceId) ||
    null;
  const connectedCount = normalizedDevices.filter(
    (device) => terminalStatuses[device.deviceId]?.state === "connected"
  ).length;

  if (normalizedDevices.length === 0) {
    return (
      <section className="web-cli-panel web-cli-panel-terminal-first web-terminal-panel terminal-workspace-panel">
        <div className="section-title-row">
          <div>
            <h4>Terminal Workspace</h4>
            <p className="muted">
              Open interactive PTY-backed terminal tabs for lab devices.
            </p>
          </div>

          <span className="badge neutral">No Devices</span>
        </div>

        <MessageBox
          type="info"
          title="No terminal devices"
          message="CLI access information is not available yet."
        />
      </section>
    );
  }

  return (
    <section className="web-cli-panel web-cli-panel-terminal-first web-terminal-panel terminal-workspace-panel">
      <div className="section-title-row">
        <div>
          <h4>Terminal Workspace</h4>
          <p className="muted">
            Keep multiple device terminals open and switch tabs without closing active sessions.
          </p>
        </div>

        <span className="badge pass">
          {connectedCount} Connected
        </span>
      </div>

      <div className="terminal-workspace-summary">
        <div>
          <span>Active Tab</span>
          <strong>{activeDevice?.label || "No active device"}</strong>
        </div>

        <div>
          <span>Open Device Tabs</span>
          <strong>{normalizedDevices.length}</strong>
        </div>

        <div>
          <span>Live Sessions</span>
          <strong>{connectedCount}</strong>
        </div>

        <div>
          <span>Endpoint</span>
          <strong>/terminal/ws</strong>
        </div>
      </div>

      <div
        className="terminal-workspace-tabs"
        role="tablist"
        aria-label="Device terminal tabs"
      >
        {normalizedDevices.map((device) => {
          const status = terminalStatuses[device.deviceId]?.state || "idle";
          const isActive = activeDeviceId === device.deviceId;

          return (
            <button
              aria-controls={`terminal-panel-${device.deviceId}`}
              aria-selected={isActive}
              className={`terminal-device-tab ${isActive ? "active" : ""} ${status}`}
              key={device.deviceId}
              onClick={() => setActiveDeviceId(device.deviceId)}
              role="tab"
              type="button"
            >
              <span className="terminal-tab-title">{device.label}</span>
              <span className="terminal-tab-device-id">{device.deviceId}</span>
              <span className={`terminal-tab-status badge ${getStatusBadgeClass(status)}`}>
                {formatConnectionState(status)}
              </span>
            </button>
          );
        })}
      </div>

      <div className="terminal-workspace-panels">
        {normalizedDevices.map((device) => (
          <TerminalPane
            active={activeDeviceId === device.deviceId}
            device={device}
            key={`${sessionId || "session"}-${device.deviceId}`}
            mode={mode}
            onStatusChange={handleStatusChange}
            sessionId={sessionId}
          />
        ))}
      </div>

      <div className="web-cli-help-stack">
        <MessageBox
          type="info"
          title="Safe multi-terminal access"
          message="Each device tab uses trusted lab metadata and its own WebSocket session. Closing or disconnecting one tab does not close the other terminal tabs."
        />

        <p className="footer-note">
          Backend terminal concurrency is used through /terminal/ws. Terminal tabs stay mounted so output and scrollback are preserved while switching devices.
        </p>
      </div>
    </section>
  );
}

export default WebCliTerminal;
