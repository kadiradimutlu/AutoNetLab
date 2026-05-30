import { useEffect, useMemo, useRef, useState } from "react";
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
  const terminalRef = useRef(null);
  const fitAddonRef = useRef(null);
  const terminalContainerRef = useRef(null);
  const dataDisposableRef = useRef(null);
  const resizeObserverRef = useRef(null);
  const reconnectTargetRef = useRef({
    sessionId: "",
    deviceId: ""
  });

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
  const [webCliError, setWebCliError] = useState("");
  const [webCliErrorDetails, setWebCliErrorDetails] = useState("");
  const [readiness, setReadiness] = useState(null);

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
    fitAddon.fit();
    terminal.writeln("AutoNetLab Real Terminal");
    terminal.writeln("Select a device, check readiness, then connect.");
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
      fitTerminal();
      sendResizeFrame();
    });
    resizeObserverRef.current.observe(terminalContainerRef.current);

    return () => {
      dataDisposableRef.current?.dispose();
      resizeObserverRef.current?.disconnect();
      socketRef.current?.close();
      terminal.dispose();
      dataDisposableRef.current = null;
      resizeObserverRef.current = null;
      socketRef.current = null;
      terminalRef.current = null;
      fitAddonRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!selectedDeviceId && normalizedDevices.length > 0) {
      setSelectedDeviceId(normalizedDevices[0].deviceId);
    }
  }, [normalizedDevices, selectedDeviceId]);

  useEffect(() => {
    if (!sessionId || !selectedDeviceId) {
      setReadiness(null);
      return;
    }

    const timer = window.setTimeout(() => {
      checkReadiness({ silent: true });
    }, 250);

    return () => window.clearTimeout(timer);
  }, [sessionId, selectedDeviceId]);

  function writeTerminal(text = "") {
    terminalRef.current?.write(text);
  }

  function writeTerminalLine(text = "") {
    terminalRef.current?.writeln(text);
  }

  function clearTerminal() {
    terminalRef.current?.clear();
    writeTerminalLine("AutoNetLab Real Terminal");
    writeTerminalLine(selectedDeviceId ? `Selected device: ${selectedDeviceId}` : "No device selected.");
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

    if (!selectedDeviceId) {
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
      writeTerminalLine(`[system] Checking readiness for ${selectedDeviceId}...`);
    }

    try {
      const result = await getWebCliDeviceReadiness(sessionId, selectedDeviceId);
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
        deviceId: selectedDeviceId
      });

      disconnectWebTerminal({ writeMessage: false });
      reconnectTargetRef.current = {
        sessionId,
        deviceId: selectedDeviceId
      };

      clearTerminal();
      writeTerminalLine(`[system] Connecting to ${selectedDeviceId}...`);

      const socket = new WebSocket(webTerminalUrl);
      socket.binaryType = "arraybuffer";
      socketRef.current = socket;
      setConnectionState("connecting");

      socket.onopen = () => {
        setConnectionState("connected");
        writeTerminalLine("[system] WebSocket connection opened.");
        fitTerminal();
        sendResizeFrame();
        terminalRef.current?.focus();
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
    const target = reconnectTargetRef.current;

    if (target.sessionId !== sessionId || target.deviceId !== selectedDeviceId) {
      connectWebTerminal();
      return;
    }

    disconnectWebTerminal({ writeMessage: false });
    connectWebTerminal();
  }

  function handleDeviceChange(event) {
    const nextDeviceId = event.target.value;

    disconnectWebTerminal({ writeMessage: false });
    setSelectedDeviceId(nextDeviceId);
    setReadiness(null);
    setWebCliError("");
    setWebCliErrorDetails("");
    setConnectionState("idle");

    window.setTimeout(() => {
      terminalRef.current?.clear();
      writeTerminalLine("AutoNetLab Real Terminal");
      writeTerminalLine(`Selected device: ${nextDeviceId}`);
      writeTerminalLine("Check readiness, then connect.");
      writeTerminalLine("");
    }, 0);
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
    <section className="web-cli-panel web-cli-panel-terminal-first web-terminal-panel">
      <div className="section-title-row">
        <div>
          <h4>Real Web Terminal</h4>
          <p className="muted">
            Open an interactive PTY-backed terminal for the selected lab device.
          </p>
        </div>

        <span className={`badge ${statusBadgeClass}`}>
          {connectionState}
        </span>
      </div>

      <div className="web-terminal-shell-card">
        <div className="web-terminal-toolbar">
          <div>
            <span className="muted">Interactive terminal</span>
            <strong>{selectedDevice?.label || selectedDeviceId || "No device selected"}</strong>
          </div>

          <span className={`badge ${isConnected ? "pass" : "neutral"}`}>
            {isConnected ? "LIVE PTY" : "DISCONNECTED"}
          </span>
        </div>

        <div
          className="xterm-shell-container"
          ref={terminalContainerRef}
          onClick={() => terminalRef.current?.focus()}
          role="application"
          aria-label="Interactive Web Terminal"
        />
      </div>

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
          <span>Endpoint</span>
          <strong>/terminal/ws</strong>
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
            onChange={handleDeviceChange}
            disabled={isConnecting || isCheckingReadiness}
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
            onClick={connectWebTerminal}
            disabled={!canConnect || isConnected || isConnecting || isCheckingReadiness}
            title={!canConnect ? "Check readiness and deploy the lab before connecting." : "Connect to the selected device."}
            type="button"
          >
            {isConnecting ? "Connecting..." : canConnect ? "Connect Terminal" : "Not Ready"}
          </button>

          <button
            className="secondary-button"
            onClick={reconnectWebTerminal}
            disabled={!selectedDeviceId || isConnecting || isCheckingReadiness}
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
            disabled={!selectedDeviceId}
            title="Clear the visible terminal screen."
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

      <div className="web-cli-help-stack">
        <MessageBox
          type="info"
          title="Safe Web Terminal access"
          message="Device selection uses trusted lab metadata. Container names cannot be typed or overridden from the browser."
        />

        <p className="footer-note">
          Current mode: {mode || "browser_cli_mvp"}. Terminal input is sent directly to the backend PTY bridge.
        </p>
      </div>
    </section>
  );
}

export default WebCliTerminal;
