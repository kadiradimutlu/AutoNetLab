import { useEffect, useState } from "react";
import TopologyCard from "../components/TopologyCard";
import MessageBox from "../components/MessageBox";
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
    deviceName:
      cli.device_name ||
      cli.device ||
      cli.device_id ||
      cli.container_name ||
      `device-${index + 1}`,
    containerName:
      cli.container_name ||
      cli.container ||
      cli.container_id ||
      "-",
    accessMethod:
      cli.access_method ||
      cli.method ||
      "docker_exec",
    dockerExecCommand:
      cli.docker_exec_command ||
      cli.command ||
      cli.exec_command ||
      "",
    sshCommand:
      cli.ssh_command ||
      cli.ssh ||
      "",
    description:
      cli.description ||
      ""
  };
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

  useEffect(() => {
    let isMounted = true;

    async function loadCliAccess() {
      if (!labSession?.session_id) {
        setCliAccessList([]);
        setCliAccessWarning("");
        setCliAccessDetails("");
        return;
      }

      setCliAccessWarning("");
      setCliAccessDetails("");

      try {
        const result = await getCliAccess(labSession.session_id);

        if (isMounted) {
          const normalizedResult = Array.isArray(result)
            ? result.map((cli, index) => normalizeCliAccess(cli, index))
            : [];

          setCliAccessList(normalizedResult);
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
  }, [labSession?.session_id]);

  if (!labSession) {
    return (
      <section className="card">
        <h2>{t("labSessionDetail")}</h2>
        <p className="muted">{t("labSessionLoading")}</p>
      </section>
    );
  }

  const injectedErrors = labSession.injected_errors || [];
  const fallbackCliAccess = (labSession.cli_access || []).map((cli, index) =>
    normalizeCliAccess(cli, index)
  );
  const cliAccess = cliAccessList.length > 0 ? cliAccessList : fallbackCliAccess;
  const difficultyClass = getDifficultyClass(labSession.difficulty);

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
    <div className="two-column">
      <section className="card">
        <h2>{t("labSessionDetail")}</h2>

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

        <div className="info-row">
          <span>{t("injectedErrors")}</span>
          <strong>{injectedErrors.length}</strong>
        </div>

        <h4>{t("injectedErrors")}</h4>
        <div className="result-list">
          {injectedErrors.length === 0 && (
            <p className="muted">No injected errors found.</p>
          )}

          {injectedErrors.map((error) => (
            <div className="list-item" key={`${error.code}-${error.device}`}>
              <div className="result-title-row">
                <strong>{error.code}</strong>
                <span className={`badge ${error.severity || ""}`}>
                  {error.severity || "unknown"}
                </span>
              </div>

              <p>{error.description}</p>
              <p className="muted">
                {t("topic")}: {error.topic} | {t("device")}: {error.device}
              </p>
            </div>
          ))}
        </div>

        <h4>{t("cliAccess")}</h4>

        {cliAccessWarning && (
          <>
            <MessageBox
              type="error"
              title="CLI access warning"
              message={cliAccessWarning}
            />

            {cliAccessDetails && (
              <div className="technical-detail-box">
                <strong>Technical detail</strong>
                <p>{cliAccessDetails}</p>
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

          {cliAccess.map((cli, index) => {
            const dockerCommandKey = `${cli.deviceName}-docker-${index}`;
            const sshCommandKey = `${cli.deviceName}-ssh-${index}`;

            return (
              <div className="list-item cli-card" key={`${cli.deviceName}-${index}`}>
                <div className="result-title-row">
                  <strong>{cli.deviceName}</strong>
                  <span className="badge">CLI</span>
                </div>

                <div className="cli-meta-grid">
                  <div>
                    <span className="muted">Container Name</span>
                    <strong>{cli.containerName}</strong>
                  </div>

                  <div>
                    <span className="muted">Access Method</span>
                    <strong>{cli.accessMethod}</strong>
                  </div>
                </div>

                <p className="muted">
                  Description: Use this command to access {cli.deviceName} through the CLI.
                </p>

                {cli.dockerExecCommand && (
                  <div className="command-section">
                    <p className="muted">Docker Exec Command:</p>

                    <div className="command-row">
                      <code className="command-box">{cli.dockerExecCommand}</code>

                      <button
                        className="secondary-button"
                        onClick={() =>
                          handleCopyCommand(
                            cli.dockerExecCommand,
                            dockerCommandKey
                          )
                        }
                      >
                        {copiedCommandKey === dockerCommandKey
                          ? "Copied"
                          : "Copy"}
                      </button>
                    </div>
                  </div>
                )}

                {cli.sshCommand && (
                  <div className="command-section">
                    <p className="muted">SSH Command:</p>

                    <div className="command-row">
                      <code className="command-box">{cli.sshCommand}</code>

                      <button
                        className="secondary-button"
                        onClick={() =>
                          handleCopyCommand(cli.sshCommand, sshCommandKey)
                        }
                      >
                        {copiedCommandKey === sshCommandKey ? "Copied" : "Copy"}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        <h4>Containerlab Runtime</h4>

        <div className="actions">
          <button
            className="primary-button"
            onClick={handleDeployLab}
            disabled={isDeploying || isDestroying}
          >
            {isDeploying ? "Deploying..." : "Deploy Lab"}
          </button>

          <button
            className="primary-button"
            onClick={handleDestroyLab}
            disabled={isDeploying || isDestroying}
          >
            {isDestroying ? "Destroying..." : "Destroy Lab"}
          </button>

          <button className="primary-button" onClick={() => onNavigate("result")}>
            {t("validateLab")}
          </button>
        </div>

        {operationError && (
          <>
            <MessageBox
              type="error"
              title="Operation failed"
              message={operationError}
            />

            {operationErrorDetails && (
              <div className="technical-detail-box">
                <strong>Technical detail</strong>
                <p>{operationErrorDetails}</p>
              </div>
            )}
          </>
        )}

        {operationResult && (
          <div className="result-list runtime-result">
            <div className="list-item">
              <strong>
                Runtime operation result: {operationResult.status || "unknown"}
              </strong>

              {operationResult.message && <p>{operationResult.message}</p>}

              {operationResult.return_code !== undefined &&
                operationResult.return_code !== null &&
                operationResult.return_code !== "" && (
                  <p className="muted">
                    Return code: {operationResult.return_code}
                  </p>
                )}

              {operationResult.stderr && (
                <p className="muted">stderr: {operationResult.stderr}</p>
              )}

              {operationResult.stdout && (
                <p className="muted">stdout: {operationResult.stdout}</p>
              )}
            </div>
          </div>
        )}

        <p className="footer-note">{t("backendFormatNote")}</p>
      </section>

      <TopologyCard topology={labSession.topology} />
    </div>
  );
}

export default SessionDetail;