import { useEffect, useRef, useState } from "react";
import MessageBox from "../components/MessageBox";
import TopologyCard from "../components/TopologyCard";
import WebCliTerminal from "../components/WebCliTerminal";
import DeviceCliCard from "../components/DeviceCliCard";
import ScenarioOverview from "../components/ScenarioOverview";
import {
  deployLab,
  destroyLab,
  finishLab,
  getCliAccess,
  getErrorDetails,
  getErrorMessage,
  getLab,
  getLabHints,
  getValidationHistory
} from "../services/apiService";
import { useLanguage } from "../hooks/useLanguage";
import {
  formatDifficulty,
  formatStatus,
  formatStudentName,
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

function isRuntimeActiveStatus(status) {
  const normalizedStatus = String(status || "").toLowerCase();

  return (
    normalizedStatus.includes("deployed") ||
    normalizedStatus.includes("validated") ||
    normalizedStatus.includes("active")
  );
}

function isRuntimeFinishedStatus(status) {
  const normalizedStatus = String(status || "").toLowerCase();

  return (
    normalizedStatus.includes("finished") ||
    normalizedStatus.includes("error")
  );
}

function isRuntimeDestroyedStatus(status) {
  return String(status || "").toLowerCase().includes("destroyed");
}

function getAttemptStatusLabel(attempt) {
  if (attempt?.passed === true) {
    return "Passed";
  }

  if (attempt?.passed === false) {
    return "Needs work";
  }

  return "Unknown";
}

function getAttemptBadgeClass(attempt) {
  if (attempt?.passed === true) {
    return "pass";
  }

  if (attempt?.passed === false) {
    return "fail";
  }

  return "neutral";
}

function formatAttemptDateTime(value) {
  if (!value) {
    return "-";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return date.toLocaleString("en-US", {
    dateStyle: "medium",
    timeStyle: "short"
  });
}

function LabWorkspacePage({ labSession, onLabUpdated, onNavigate }) {
  const { t } = useLanguage();
  const [cliAccessList, setCliAccessList] = useState([]);
  const [cliAccessMode, setCliAccessMode] = useState("local_docker_exec_demo");
  const [cliAccessWarning, setCliAccessWarning] = useState("");
  const [cliAccessDetails, setCliAccessDetails] = useState("");
  const [copiedCommandKey, setCopiedCommandKey] = useState("");
  const [copyNotice, setCopyNotice] = useState("");
  const [isStartingLab, setIsStartingLab] = useState(false);
  const [isStoppingLab, setIsStoppingLab] = useState(false);
  const [isResettingLab, setIsResettingLab] = useState(false);
  const [lifecycleMessage, setLifecycleMessage] = useState("");
  const [lifecycleError, setLifecycleError] = useState("");
  const [lifecycleDetails, setLifecycleDetails] = useState("");
  const [activeWorkspaceTab, setActiveWorkspaceTab] = useState("sessionDetail");
  const [hints, setHints] = useState([]);
  const [isLoadingHints, setIsLoadingHints] = useState(false);
  const [hintsWarning, setHintsWarning] = useState("");
  const [hintsDetails, setHintsDetails] = useState("");
  const [attempts, setAttempts] = useState([]);
  const [isLoadingAttempts, setIsLoadingAttempts] = useState(false);
  const [attemptsWarning, setAttemptsWarning] = useState("");
  const [attemptsDetails, setAttemptsDetails] = useState("");
  const workspaceTabsRef = useRef(null);

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

  useEffect(() => {
    let isMounted = true;

    async function loadHints() {
      if (!labSession?.session_id) {
        setHints([]);
        setHintsWarning("");
        setHintsDetails("");
        return;
      }

      setIsLoadingHints(true);
      setHintsWarning("");
      setHintsDetails("");

      try {
        const result = await getLabHints(labSession.session_id);

        if (isMounted) {
          setHints(Array.isArray(result?.hints) ? result.hints : []);
        }
      } catch (error) {
        console.error("Workspace hints fetch failed.", error);

        if (isMounted) {
          setHints([]);
          setHintsWarning(
            getErrorMessage(
              error,
              "Hints could not be loaded for this lab."
            )
          );
          setHintsDetails(getErrorDetails(error));
        }
      } finally {
        if (isMounted) {
          setIsLoadingHints(false);
        }
      }
    }

    loadHints();

    return () => {
      isMounted = false;
    };
  }, [labSession?.session_id]);

  useEffect(() => {
    let isMounted = true;

    async function loadValidationHistory() {
      if (!labSession?.session_id) {
        setAttempts([]);
        setAttemptsWarning("");
        setAttemptsDetails("");
        return;
      }

      setIsLoadingAttempts(true);
      setAttemptsWarning("");
      setAttemptsDetails("");

      try {
        const result = await getValidationHistory(labSession.session_id);

        if (isMounted) {
          setAttempts(Array.isArray(result?.attempts) ? result.attempts : []);
        }
      } catch (error) {
        console.error("Validation history fetch failed.", error);

        if (isMounted) {
          setAttempts([]);
          setAttemptsWarning(
            getErrorMessage(
              error,
              "Validation history could not be loaded for this lab."
            )
          );
          setAttemptsDetails(getErrorDetails(error));
        }
      } finally {
        if (isMounted) {
          setIsLoadingAttempts(false);
        }
      }
    }

    loadValidationHistory();

    return () => {
      isMounted = false;
    };
  }, [labSession?.session_id, labSession?.status]);

  function handleWorkspaceTabChange(tabId) {
    setActiveWorkspaceTab(tabId);

    if (typeof window !== "undefined") {
      window.requestAnimationFrame(() => {
        window.scrollTo({
          top: 0,
          behavior: "auto"
        });
      });
    }
  }

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

      setLifecycleMessage("Lab deployed successfully. Open the Lab Console tab to review topology and connect to devices.");
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

  async function handleResetLabRuntime() {
    if (!labSession?.session_id) {
      return;
    }

    const shouldReset = window.confirm(
      "Reset this lab runtime? Running containers will be removed. You can deploy the same lab again from this workspace."
    );

    if (!shouldReset) {
      return;
    }

    setIsResettingLab(true);
    setLifecycleMessage("");
    setLifecycleError("");
    setLifecycleDetails("");

    try {
      await destroyLab(labSession.session_id);
      await refreshLabSession();
      setLifecycleMessage("Lab runtime reset successfully. Deploy the lab again when you are ready.");
    } catch (error) {
      setLifecycleError(getErrorMessage(error, "Lab runtime could not be reset."));
      setLifecycleDetails(getErrorDetails(error));
      console.error("Lab runtime reset failed.", error);
    } finally {
      setIsResettingLab(false);
    }
  }

  async function handleStopLabEnvironment() {
    if (!labSession?.session_id) {
      return;
    }

    const shouldStop = window.confirm(
      "Finish this lab? Running containers will be stopped, but validation history and results will be preserved."
    );

    if (!shouldStop) {
      return;
    }

    setIsStoppingLab(true);
    setLifecycleMessage("");
    setLifecycleError("");
    setLifecycleDetails("");

    try {
      await finishLab(labSession.session_id);
      const refreshedLab = await refreshLabSession();

      setLifecycleMessage("Lab finished successfully. Validation history is preserved.");
      setCliAccessList([]);
      setCliAccessMode(getFallbackCliMode(refreshedLab || labSession));
    } catch (error) {
      setLifecycleError(getErrorMessage(error, "Lab could not be finished."));
      setLifecycleDetails(getErrorDetails(error));
      console.error("Lab finish failed.", error);
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
  const isLabRunning = isRuntimeActiveStatus(normalizedStatus);
  const isLabStopped = isRuntimeDestroyedStatus(normalizedStatus);
  const isLabFinished = isRuntimeFinishedStatus(normalizedStatus);

  const workspaceActions = (
    <div className="workspace-topology-actions">
      {!isLabRunning && !isLabStopped && !isLabFinished && (
        <button
          className="primary-button"
          onClick={handleStartLabEnvironment}
          disabled={isStartingLab || isStoppingLab || isResettingLab}
          type="button"
        >
          {isStartingLab ? "Starting..." : "Deploy Lab"}
        </button>
      )}

      {isLabRunning && (
        <>
          <button
            className="secondary-button"
            onClick={handleResetLabRuntime}
            disabled={isStartingLab || isStoppingLab || isResettingLab}
            type="button"
          >
            {isResettingLab ? "Resetting..." : "Reset Runtime"}
          </button>

          <button
            className="danger-button"
            onClick={handleStopLabEnvironment}
            disabled={isStartingLab || isStoppingLab || isResettingLab}
            type="button"
          >
            {isStoppingLab ? "Finishing..." : "Finish Lab"}
          </button>
        </>
      )}

      {isLabStopped && !isLabFinished && (
        <button
          className="primary-button"
          onClick={handleStartLabEnvironment}
          disabled={isStartingLab || isStoppingLab || isResettingLab}
          type="button"
        >
          {isStartingLab ? "Starting..." : "Deploy Lab"}
        </button>
      )}

      {isLabFinished && (
        <button
          className="primary-button"
          onClick={() => onNavigate("create")}
          type="button"
        >
          Create New Lab
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
            Review the topology, deploy the lab, use the Web CLI,
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
                    <summary>Show diagnostics</summary>
                    <p>{lifecycleDetails}</p>
                  </details>
                )}
              </>
            )}
          </div>
        )}
      </section>

      <section className="card workspace-tabs-card">
        <div className="workspace-tab-list" role="tablist" ref={workspaceTabsRef} aria-label="Workspace sections">
          <button
            className={activeWorkspaceTab === "sessionDetail" ? "active" : ""}
            type="button"
            role="tab"
            aria-selected={activeWorkspaceTab === "sessionDetail"}
            onClick={() => handleWorkspaceTabChange("sessionDetail")}
          >
            Session Detail
          </button>

          <button
            className={activeWorkspaceTab === "labConsole" ? "active" : ""}
            type="button"
            role="tab"
            aria-selected={activeWorkspaceTab === "labConsole"}
            onClick={() => handleWorkspaceTabChange("labConsole")}
          >
            Lab Console
          </button>

          <button
            className={activeWorkspaceTab === "history" ? "active" : ""}
            type="button"
            role="tab"
            aria-selected={activeWorkspaceTab === "history"}
            onClick={() => handleWorkspaceTabChange("history")}
          >
            History
            {attempts.length > 0 && (
              <span className="tab-count">{attempts.length}</span>
            )}
          </button>
        </div>
      </section>

      {activeWorkspaceTab === "sessionDetail" && (
        <section className="card workspace-session-detail-card">
          <h3>Session Detail</h3>

          <ScenarioOverview labSession={labSession} t={t} />

          <div className="workspace-session-detail-grid">
            <div className="info-row">
              <span>Session ID</span>
              <strong>{labSession.session_id}</strong>
            </div>

            <div className="info-row">
              <span>Student</span>
              <strong>{formatStudentName(labSession.student_id)}</strong>
            </div>

            <div className="info-row">
              <span>Difficulty</span>
              <span className={`badge ${difficultyClass}`}>
                {formatDifficulty(labSession.difficulty, t)}
              </span>
            </div>

            <div className="info-row">
              <span>Status</span>
              <strong>{formatStatus(labSession.status, t)}</strong>
            </div>
          </div>
        </section>
      )}
      {activeWorkspaceTab === "labConsole" && (
        <div className="lab-console-workspace">
          <TopologyCard
            topology={labSession.topology}
            difficulty={labSession.difficulty}
            status={labSession.status}
            cliAccess={cliAccess}
            variant="workspace"
            actions={null}
          />

      <section className="card lab-workspace-terminal-card">
        <div className="section-title-row">
          <div>
            <h3>Browser Terminal</h3>
            <p className="muted">
              Web CLI is available while the lab is deployed or validated.
            </p>
          </div>

          <span className="badge neutral">Web CLI</span>
        </div>

        {!isLabRunning && (
          <MessageBox
            type="info"
            title="Web CLI is not active"
            message={
              isLabFinished
                ? "This lab is finished. Running containers are closed, but validation history remains available."
                : "Deploy the lab before opening Web CLI."
            }
          />
        )}

        {isLabRunning && (
          <>
            {cliAccessWarning && (
              <>
                <MessageBox
                  type="error"
                  title="CLI access warning"
                  message={cliAccessWarning}
                />

                {cliAccessDetails && (
                  <details className="technical-detail-box">
                    <summary>Show diagnostics</summary>
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
          </>
        )}
      </section>
        </div>
      )}

      {activeWorkspaceTab === "history" && (
        <section className="card workspace-history-card">
          <div className="section-title-row">
            <div>
              <h3>Validation History</h3>
              <p className="muted">
                Review previous validation runs and track progress while improving the live configuration.
              </p>
            </div>

            <span className="badge neutral">{attempts.length} records</span>
          </div>

          {isLoadingAttempts && (
            <MessageBox
              type="info"
              title="Loading history"
              message="Loading validation history for this lab."
            />
          )}

          {attemptsWarning && (
            <>
              <MessageBox
                type="error"
                title="Validation history could not be loaded"
                message={attemptsWarning}
              />

              {attemptsDetails && (
                <details className="technical-detail-box">
                  <summary>Show diagnostics</summary>
                  <p>{attemptsDetails}</p>
                </details>
              )}
            </>
          )}

          {!isLoadingAttempts && !attemptsWarning && attempts.length === 0 && (
            <MessageBox
              type="info"
              title="No validation attempts yet"
              message="Run validation to create the first attempt record for this lab."
            />
          )}

          {!isLoadingAttempts && !attemptsWarning && attempts.length > 0 && (
            <div className="result-list">
              {attempts.map((attempt) => (
                <article className="list-item" key={attempt.attempt_number}>
                  <div className="result-title-row">
                    <div>
                      <strong>Attempt {attempt.attempt_number}</strong>
                      <p className="muted">{formatAttemptDateTime(attempt.created_at)}</p>
                    </div>

                    <span className={`badge ${getAttemptBadgeClass(attempt)}`}>
                      {getAttemptStatusLabel(attempt)}
                    </span>
                  </div>

                  <div className="validation-compact-summary">
                    <div>
                      <span>Score</span>
                      <strong>{attempt.score ?? "-"}/100</strong>
                    </div>

                    <div>
                      <span>Passed Checks</span>
                      <strong>{attempt.passed_checks ?? "-"}</strong>
                    </div>

                    <div>
                      <span>Failed Checks</span>
                      <strong>{attempt.failed_checks ?? "-"}</strong>
                    </div>

                    <div>
                      <span>Total Checks</span>
                      <strong>{attempt.total_checks ?? "-"}</strong>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      )}

    </div>
  );
}

export default LabWorkspacePage;
