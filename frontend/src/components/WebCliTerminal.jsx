import { useEffect, useMemo, useRef, useState } from "react";
import MessageBox from "./MessageBox";
import {
  getAuthToken,
  getErrorMessage,
  getWebCliUrl
} from "../services/apiService";

const READABLE_WEB_CLI_ERRORS = {
  WEB_CLI_AUTH_REQUIRED: "Authentication is required before opening Web CLI.",
  WEB_CLI_INVALID_TOKEN: "Your login token is invalid. Please log out and sign in again.",
  WEB_CLI_FORBIDDEN: "This user is not allowed to access the selected lab device.",
  WEB_CLI_SESSION_NOT_FOUND: "The selected lab session could not be found.",
  WEB_CLI_DEVICE_NOT_FOUND: "The selected device is not available for this lab session.",
  LAB_NOT_DEPLOYED_FOR_WEB_CLI: "Deploy the lab before opening Web CLI.",
  DOCKER_NOT_FOUND_FOR_WEB_CLI: "Docker is not available for Web CLI on the backend host.",
  DOCKER_PERMISSION_DENIED_FOR_WEB_CLI: "The backend does not have permission to access Docker for Web CLI.",
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
      const friendlyMessage =
        READABLE_WEB_CLI_ERRORS[parsedMessage.error_code] ||
        parsedMessage.message ||
        "Web CLI returned an error.";

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
  const [connectionState, setConnectionState] = useState("disconnected");
  const [command, setCommand] = useState("");
  const [terminalLines, setTerminalLines] = useState([
    {
      kind: "system",
      text: "Web CLI is ready. Select a device and connect after deploying the lab."
    }
  ]);
  const [webCliError, setWebCliError] = useState("");

  useEffect(() => {
    if (!selectedDeviceId && normalizedDevices.length > 0) {
      setSelectedDeviceId(normalizedDevices[0].deviceId);
    }
  }, [normalizedDevices, selectedDeviceId]);

  useEffect(() => {
    outputEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [terminalLines]);

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

  function connectWebCli() {
    setWebCliError("");

    if (!sessionId) {
      setWebCliError("A lab session is required before opening Web CLI.");
      return;
    }

    if (!selectedDeviceId) {
      setWebCliError("Select a device before opening Web CLI.");
      return;
    }

    if (!getAuthToken()) {
      setWebCliError("A login token is required before opening Web CLI.");
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

  const isConnected = connectionState === "connected";
  const isConnecting = connectionState === "connecting";

  return (
    <section className="web-cli-panel">
      <div className="section-title-row">
        <div>
          <h4>Web CLI MVP</h4>
          <p className="muted">
            Open a browser-based CLI session for the selected lab device. Deploy the lab before connecting.
          </p>
        </div>

        <span className={`badge ${isConnected ? "pass" : "neutral"}`}>
          {connectionState}
        </span>
      </div>

      <MessageBox
        type="info"
        title="Safe Web CLI access"
        message="Device selection uses trusted backend lab metadata. Container names cannot be typed or overridden from the browser."
      />

      {webCliError && (
        <MessageBox
          type="error"
          title="Web CLI message"
          message={webCliError}
        />
      )}

      <div className="web-cli-controls">
        <div className="form-group">
          <label htmlFor="web-cli-device">Device</label>
          <select
            id="web-cli-device"
            value={selectedDeviceId}
            onChange={(event) => setSelectedDeviceId(event.target.value)}
            disabled={isConnected || isConnecting}
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
            className="primary-button"
            onClick={connectWebCli}
            disabled={isConnected || isConnecting || normalizedDevices.length === 0}
            type="button"
          >
            {isConnecting ? "Connecting..." : "Connect Web CLI"}
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

      <p className="footer-note">
        Current mode: {mode || "browser_cli_mvp"}. Local Docker Exec commands remain available below as a fallback.
      </p>
    </section>
  );
}

export default WebCliTerminal;
