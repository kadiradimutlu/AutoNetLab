import { useEffect, useState } from "react";
import MessageBox from "../components/MessageBox";
import TopologyCard from "../components/TopologyCard";
import WebCliTerminal from "../components/WebCliTerminal";
import DeviceCliCard from "../components/DeviceCliCard";
import {
  deployLab,
  destroyLab,
  getCliAccess,
  getErrorDetails,
  getErrorMessage,
  getLab
} from "../services/apiService";
import {
  formatDifficulty,
  formatStatus,
  getDifficultyClass
} from "../utils/formatters";

function normalizeCliAccess(cli, index) {
  return {
    deviceId:
      cli.deviceId ||
      cli.device_id ||
      cli.device ||
      cli.name ||
      cli.device_name ||
      `device-${index + 1}`,
    deviceName:
      cli.deviceName ||
      cli.device_name ||
      cli.name ||
      cli.device ||
      cli.device_id ||
      cli.container_name ||
      `device-${index + 1}`,
    containerName:
      cli.containerName ||
      cli.container_name ||
      cli.container ||
      cli.container_id ||
      "-",
    accessMethod:
      cli.accessMethod ||
      cli.access_method ||
      cli.method ||
      "local_docker_exec_demo",
    dockerExecCommand:
      cli.dockerExecCommand ||
      cli.docker_exec_command ||
      cli.command ||
      cli.exec_command ||
      "",
    sshCommand:
      cli.sshCommand ||
      cli.ssh_command ||
      cli.ssh ||
      "",
    description:
      cli.description ||
      ""
  };
}

function normalizeCliAccessResponse(result) {
  if (Array.isArray(result)) {
    return {
      mode: "local_docker_exec_demo",
      cliAccess: result.map((cli, index) => normalizeCliAccess(cli, index))
    };
  }

  const safeResult = result && typeof result === "object" ? result : {};
  const items =
    safeResult.cli_access ||
    safeResult.devices ||
    safeResult.items ||
    [];

  return {
    mode:
      safeResult.mode ||
      safeResult.cli_mode ||
      safeResult.access_mode ||
      "local_docker_exec_demo",
    cliAccess: Array.isArray(items)
      ? items.map((cli, index) => normalizeCliAccess(cli, index))
      : []
  };
}

function getFallbackCliMode(labSession) {
  return (
    labSession?.cli_access_mode ||
    labSession?.cli_mode ||
    labSession?.access_mode ||
    labSession?.mode ||
    "local_docker_exec_demo"
  );
}

function LabWorkspacePage({ labSession, onLabUpdated, onNavigate }) {
  const [cliAccessList, setCliAccessList] = useState([]);
  const [cliAccessMode, setCliAccessMode] = useState("local_docker_exec_demo");
  const [cliAccessWarning, setCliAccessWarning] = useState("");
  const [cliAccessDetails, setCliAccessDetails] = useState("");
  const [copiedCommandKey, setCopiedCommandKey] = useState("");
  const [copyNotice, setCopyNotice] = useState("");
  const [isStartingLab, setIsStartingLab] = useState(false);
  const [isStoppingLab, setIsStoppingLab] = useState(false);
  const [lifecycleMessage, setLifecycleMessage] = useState("");
  const [lifecycleError, setLifecycleError] = useState("");
  const [lifecycleDetails, setLifecycleDetails] = useState("");
  const [activeWorkspaceTab, setActiveWorkspaceTab] = useState("topology");

  useEffect(() => {
    let isMounted = true;

    async function loadCliAccess() {
      if (!labSession?.session_id) {
        setCliAccessList([]);
        setCliAccessWarning("");
        setCliAccessDetails("");
        setCliAccessMode("local_docker_exec_demo");
        return;
      }

      setCliAccessWarning("");
      setCliAccessDetails("");
      setCliAccessMode(getFallbackCliMode(labSession));

      try {
        const result = await getCliAccess(labSession.session_id);

        if (isMounted) {
          const normalizedResult = normalizeCliAccessResponse(result);
          setCliAccessList(normalizedResult.cliAccess);
          setCliAccessMode(normalizedResult.mode);
        }
      } catch (error) {
        console.error("Workspace CLI access fetch failed. Falling back to session data.", error);

        if (isMounted) {
          setCliAccessList([]);
          setCliAccessWarning(
            getErrorMessage(
              error,
              "CLI access information could not be loaded. Existing session data will be used if available."
            )
          );
          setCliAccessDetails(getErrorDetails(error));
        }
      }
    }

    loadCliAccess();

    return () => {
      isMounted = false;
    };
  }, [labSession]);

  async function refreshLabSession() {
    if (!labSession?.session_id) {
      return null;
    }

    const refreshedLab = await getLab(labSession.session_id);

    if (onLabUpdated) {
      onLabUpdated(refreshedLab);
    }

    return refreshedLab;
  }

  async function handleStartLabEnvironment() {
    if (!labSession?.session_id) {
      return;
    }

    setIsStartingLab(true);
    setLifecycleMessage("");
    setLifecycleError("");
    setLifecycleDetails("");

    try {
      await deployLab(labSession.session_id);
      const refreshedLab = await refreshLabSession();

      setLifecycleMessage("Lab deployed successfully. Open the Web CLI tab to connect to devices.");
      setCliAccessList([]);
      setCliAccessMode(getFallbackCliMode(refreshedLab || labSession));
    } catch (error) {
      setLifecycleError(getErrorMessage(error, "Lab could not be deployed."));
      setLifecycleDetails(getErrorDetails(error));
      console.error("Lab deploy failed.", error);
    } finally {
      setIsStartingLab(false);
    }
  }

  async function handleStopLabEnvironment() {
    if (!labSession?.session_id) {
      return;
    }

    const shouldStop = window.confirm(
      "Destroy this lab? Running device containers will be removed."
    );

    if (!shouldStop) {
      return;
    }

    setIsStoppingLab(true);
    setLifecycleMessage("");
    setLifecycleError("");
    setLifecycleDetails("");

    try {
      await destroyLab(labSession.session_id);
      const refreshedLab = await refreshLabSession();

      setLifecycleMessage("Lab destroyed successfully.");
      setCliAccessList([]);
      setCliAccessMode(getFallbackCliMode(refreshedLab || labSession));
    } catch (error) {
      setLifecycleError(getErrorMessage(error, "Lab could not be destroyed."));
      setLifecycleDetails(getErrorDetails(error));
      console.error("Lab destroy failed.", error);
    } finally {
      setIsStoppingLab(false);
    }
  }

  async function handleCopyCommand(command, commandKey) {
    if (!command) {
      return;
    }

    setCopyNotice("");

    try {
      await navigator.clipboard.writeText(command);
      setCopiedCommandKey(commandKey);
      setCopyNotice("Command copied to clipboard.");

      setTimeout(() => {
        setCopiedCommandKey("");
        setCopyNotice("");
      }, 1500);
    } catch (error) {
      console.error("Copy command failed.", error);
      setCliAccessWarning("Command could not be copied. Please copy it manually.");
      setCliAccessDetails(error.message || "");
    }
  }

  if (!labSession) {
    return (
      <section className="card">
        <h2>Lab Workspace</h2>
        <p className="muted">
          Create or open a lab session before entering the workspace.
        </p>

        <div className="actions">
          <button className="primary-button" onClick={() => onNavigate("create")}>
            Create Lab
          </button>

          <button className="secondary-button" onClick={() => onNavigate("home")}>
            Back to Home
          </button>
        </div>
      </section>
    );
  }

  const fallbackCliAccess = (labSession.cli_access || []).map((cli, index) =>
    normalizeCliAccess(cli, index)
  );
  const cliAccess = cliAccessList.length > 0 ? cliAccessList : fallbackCliAccess;
  const effectiveCliMode = cliAccessMode || getFallbackCliMode(labSession);
  const normalizedStatus = String(labSession.status || "").toLowerCase();
  const isLabRunning = normalizedStatus.includes("deployed") || normalizedStatus.includes("active");
  const isLabStopped = normalizedStatus.includes("destroyed");

  const workspaceActions = (
    <div className="workspace-topology-actions">
      {!isLabRunning && !isLabStopped && (
        <button
          className="primary-button"
          onClick={handleStartLabEnvironment}
          disabled={isStartingLab || isStoppingLab}
          type="button"
        >
          {isStartingLab ? "Starting..." : "Deploy Lab"}
        </button>
      )}

      {isLabRunning && (
        <button
          className="danger-button"
          onClick={handleStopLabEnvironment}
          disabled={isStartingLab || isStoppingLab}
          type="button"
        >
          {isStoppingLab ? "Stopping..." : "Destroy Lab"}
        </button>
      )}

      {isLabStopped && (
        <button
          className="primary-button"
          onClick={handleStartLabEnvironment}
          disabled={isStartingLab || isStoppingLab}
          type="button"
        >
          {isStartingLab ? "Starting..." : "Deploy Lab"}
        </button>
      )}

      <button className="secondary-button" onClick={() => onNavigate("myLabs")} type="button">
        My Labs
      </button>

      <button className="primary-button" onClick={() => onNavigate("result")} type="button">
        Validate Solution
      </button>
    </div>
  );
  const difficultyClass = getDifficultyClass(labSession.difficulty);

  return (
    <div className="lab-workspace-page">
      <section className="card workspace-action-card">
        <div>
          <h3>Lab Workspace</h3>
          <p className="muted">
            Review the topology, deploy the lab, open the Web CLI,
            and validate your solution from this workspace.
          </p>
        </div>

        {workspaceActions}

        {(lifecycleMessage || lifecycleError) && (
          <div className="workspace-lifecycle-feedback workspace-lifecycle-feedback-inline">
            {lifecycleMessage && (
              <MessageBox
                type="success"
                title="Lab updated"
                message={lifecycleMessage}
              />
            )}

            {lifecycleError && (
              <>
                <MessageBox
                  type="error"
                  title="Lab operation failed"
                  message={lifecycleError}
                />

                {lifecycleDetails && (
                  <details className="technical-detail-box">
                    <summary>Show technical details</summary>
                    <p>{lifecycleDetails}</p>
                  </details>
                )}
              </>
            )}
          </div>
        )}
      </section>

      <section className="card workspace-tabs-card">
        <div className="workspace-tab-list" role="tablist" aria-label="Workspace sections">
          <button
            className={activeWorkspaceTab === "topology" ? "active" : ""}
            type="button"
            role="tab"
            aria-selected={activeWorkspaceTab === "topology"}
            onClick={() => setActiveWorkspaceTab("topology")}
          >
            Topology
          </button>

          <button
            className={activeWorkspaceTab === "webCli" ? "active" : ""}
            type="button"
            role="tab"
            aria-selected={activeWorkspaceTab === "webCli"}
            onClick={() => setActiveWorkspaceTab("webCli")}
          >
            Web CLI
          </button>
        </div>
      </section>

      {activeWorkspaceTab === "topology" && (
      <TopologyCard
        topology={labSession.topology}
        difficulty={labSession.difficulty}
        status={labSession.status}
        cliAccess={cliAccess}
        variant="workspace"
        actions={null}
      />
      )}
{activeWorkspaceTab === "webCli" && (
      <section className="card lab-workspace-terminal-card">
        <div className="section-title-row">
          <div>
            <h3>Browser Terminal</h3>
            <p className="muted">
              Deploy the lab first, then select a device and open the browser-based CLI.
            </p>
          </div>

          <span className="badge neutral">Web CLI</span>
        </div>

        {cliAccessWarning && (
          <>
            <MessageBox
              type="error"
              title="CLI access warning"
              message={cliAccessWarning}
            />

            {cliAccessDetails && (
              <details className="technical-detail-box">
                <summary>Show technical details</summary>
                <p>{cliAccessDetails}</p>
              </details>
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
          sessionId={labSession.session_id}
          devices={cliAccess}
          mode={effectiveCliMode}
        />

        <details className="workspace-fallback-details">
          <summary>Alternative CLI commands</summary>

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
                onCopyCommand={handleCopyCommand}
              />
            ))}
          </div>
        </details>
      </section>
      )}
    </div>
  );
}

export default LabWorkspacePage;
