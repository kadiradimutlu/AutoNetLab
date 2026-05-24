import { useEffect, useState } from "react";
import MessageBox from "../components/MessageBox";
import CliAccessPanel from "../components/CliAccessPanel";
import ScenarioOverview from "../components/ScenarioOverview";
import {
  deployLab,
  destroyLab,
  getCliAccess,
  getErrorDetails,
  getErrorMessage,
  getLab
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
    labSession.cli_access_mode ||
    labSession.cli_mode ||
    labSession.access_mode ||
    labSession.mode ||
    "local_docker_exec_demo"
  );
}

function SessionDetail({ labSession, onLabUpdated, onNavigate }) {
  const { t } = useLanguage();

  const [isDeploying, setIsDeploying] = useState(false);
  const [isDestroying, setIsDestroying] = useState(false);
  const [operationResult, setOperationResult] = useState(null);
  const [operationError, setOperationError] = useState("");
  const [operationErrorDetails, setOperationErrorDetails] = useState("");
  const [cliAccessWarning, setCliAccessWarning] = useState("");
  const [cliAccessDetails, setCliAccessDetails] = useState("");
  const [copiedCommandKey, setCopiedCommandKey] = useState("");
  const [copyNotice, setCopyNotice] = useState("");
  const [cliAccessList, setCliAccessList] = useState([]);
  const [cliAccessMode, setCliAccessMode] = useState("local_docker_exec_demo");

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
        console.error("CLI access fetch failed. Falling back to session data.", error);

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

  if (!labSession) {
    return (
      <section className="card">
        <h2>{t("labSessionDetail")}</h2>
        <p className="muted">{t("labSessionLoading")}</p>
      </section>
    );
  }

  const fallbackCliAccess = (labSession.cli_access || []).map((cli, index) =>
    normalizeCliAccess(cli, index)
  );
  const cliAccess = cliAccessList.length > 0 ? cliAccessList : fallbackCliAccess;
  const difficultyClass = getDifficultyClass(labSession.difficulty);
  const effectiveCliMode = cliAccessMode || getFallbackCliMode(labSession);

  async function refreshCurrentSession() {
    const updatedLabSession = await getLab(labSession.session_id);

    if (onLabUpdated) {
      onLabUpdated(updatedLabSession);
    }
  }

  async function handleDeployLab() {
    setIsDeploying(true);
    setOperationResult(null);
    setOperationError("");
    setOperationErrorDetails("");

    try {
      const result = await deployLab(labSession.session_id);
      setOperationResult(result);

      try {
        await refreshCurrentSession();
      } catch (refreshError) {
        console.error("Session refresh after deploy failed.", refreshError);
      }
    } catch (error) {
      setOperationError(getErrorMessage(error, "Deploy operation failed."));
      setOperationErrorDetails(getErrorDetails(error));
      console.error("Deploy operation failed.", error);
    } finally {
      setIsDeploying(false);
    }
  }

  async function handleDestroyLab() {
    setIsDestroying(true);
    setOperationResult(null);
    setOperationError("");
    setOperationErrorDetails("");

    try {
      const result = await destroyLab(labSession.session_id);
      setOperationResult(result);

      try {
        await refreshCurrentSession();
      } catch (refreshError) {
        console.error("Session refresh after destroy failed.", refreshError);
      }
    } catch (error) {
      setOperationError(getErrorMessage(error, "Destroy operation failed."));
      setOperationErrorDetails(getErrorDetails(error));
      console.error("Destroy operation failed.", error);
    } finally {
      setIsDestroying(false);
    }
  }

  async function handleCopyCommand(command, commandKey) {
    if (!command) {
      return;
    }

    setCopyNotice("");
    setOperationError("");
    setOperationErrorDetails("");

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
      setOperationError("Command could not be copied. Please copy it manually.");
      setOperationErrorDetails(error.message || "");
    }
  }

  return (
    <div className="session-detail-overview-page">
      <section className="card">
        <h2>{t("labSessionDetail")}</h2>

        <ScenarioOverview labSession={labSession} t={t} />

        <div className="info-row">
          <span>{t("sessionId")}</span>
          <strong>{labSession.session_id}</strong>
        </div>

        <div className="info-row">
          <span>{t("student")}</span>
          <strong>{formatStudentName(labSession.student_id)}</strong>
        </div>

        <div className="info-row">
          <span>{t("difficulty")}</span>
          <span className={`badge ${difficultyClass}`}>
            {formatDifficulty(labSession.difficulty, t)}
          </span>
        </div>

        <div className="info-row">
          <span>{t("status")}</span>
          <strong>{formatStatus(labSession.status, t)}</strong>
        </div>

        <div className="workspace-entry-card">
          <div>
            <h4>Lab Workspace</h4>
            <p className="muted">
              Open the dedicated troubleshooting workspace to view the full topology and use the browser-based Web CLI.
            </p>
          </div>

          <button
            className="primary-button"
            onClick={() => onNavigate("workspace")}
            type="button"
          >
            Open Workspace
          </button>
        </div>

        <h4>Containerlab Runtime</h4>

        <div className="actions">
          <button
            className="primary-button"
            onClick={handleDeployLab}
            disabled={isDeploying || isDestroying}
          >
            {isDeploying ? "Starting..." : "Start Lab Environment"}
          </button>

          <button
            className="primary-button"
            onClick={handleDestroyLab}
            disabled={isDeploying || isDestroying}
          >
            {isDestroying ? "Stopping..." : "Stop Lab Environment"}
          </button>

          <button className="secondary-button" onClick={() => onNavigate("workspace")}>
            Open Workspace
          </button>

          <button className="primary-button" onClick={() => onNavigate("result")}>
            {t("validateLab")}
          </button>
        </div>

        {operationError && (
          <>
            <MessageBox
              type="error"
              title="Lab operation failed"
              message={operationError}
            />

            {operationErrorDetails && (
              <details className="technical-detail-box">
                <summary>Show technical details</summary>
                <p>{operationErrorDetails}</p>
              </details>
            )}
          </>
        )}

        {operationResult && (
          <div className="result-list runtime-result">
            <div className="list-item">
              <strong>
                {String(operationResult.status || "").toLowerCase() === "destroyed"
                  ? "Lab environment stopped successfully."
                  : "Lab environment is ready."}
              </strong>

              {operationResult.message && (
                <p className="muted">{operationResult.message}</p>
              )}

              {(operationResult.return_code !== undefined ||
                operationResult.stderr ||
                operationResult.stdout) && (
                <details className="technical-detail-box">
                  <summary>Show technical details</summary>

                  {operationResult.return_code !== undefined &&
                    operationResult.return_code !== null &&
                    operationResult.return_code !== "" && (
                      <p>Return code: {operationResult.return_code}</p>
                    )}

                  {operationResult.stderr && <p>stderr: {operationResult.stderr}</p>}
                  {operationResult.stdout && <p>stdout: {operationResult.stdout}</p>}
                </details>
              )}
            </div>
          </div>
        )}


      </section>


    </div>
  );
}

export default SessionDetail;
