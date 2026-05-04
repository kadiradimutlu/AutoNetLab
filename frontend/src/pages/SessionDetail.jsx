import { useState } from "react";
import TopologyCard from "../components/TopologyCard";
import { deployLab, destroyLab, getLab } from "../services/apiService";
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
      `device-${index + 1}`,
    containerName:
      cli.container_name ||
      cli.container ||
      cli.container_id ||
      "-",
    dockerExecCommand:
      cli.docker_exec_command ||
      cli.command ||
      cli.exec_command ||
      "",
    sshCommand:
      cli.ssh_command ||
      cli.ssh ||
      ""
  };
}

function SessionDetail({ labSession, onLabUpdated, onNavigate }) {
  const { t } = useLanguage();

  const [isDeploying, setIsDeploying] = useState(false);
  const [isDestroying, setIsDestroying] = useState(false);
  const [operationResult, setOperationResult] = useState(null);
  const [operationError, setOperationError] = useState("");
  const [copiedCommandKey, setCopiedCommandKey] = useState("");

  if (!labSession) {
    return (
      <section className="card">
        <h2>{t("labSessionDetail")}</h2>
        <p className="muted">{t("labSessionLoading")}</p>
      </section>
    );
  }

  const injectedErrors = labSession.injected_errors || [];
  const cliAccess = (labSession.cli_access || []).map((cli, index) =>
    normalizeCliAccess(cli, index)
  );
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

    try {
      const result = await deployLab(labSession.session_id);
      setOperationResult(result);

      try {
        await refreshCurrentSession();
      } catch (refreshError) {
        console.error("Session refresh after deploy failed.", refreshError);
      }
    } catch (error) {
      setOperationError(error.message || "Deploy operation failed.");
      console.error(error);
    } finally {
      setIsDeploying(false);
    }
  }

  async function handleDestroyLab() {
    setIsDestroying(true);
    setOperationResult(null);
    setOperationError("");

    try {
      const result = await destroyLab(labSession.session_id);
      setOperationResult(result);

      try {
        await refreshCurrentSession();
      } catch (refreshError) {
        console.error("Session refresh after destroy failed.", refreshError);
      }
    } catch (error) {
      setOperationError(error.message || "Destroy operation failed.");
      console.error(error);
    } finally {
      setIsDestroying(false);
    }
  }

  async function handleCopyCommand(command, commandKey) {
    if (!command) {
      return;
    }

    try {
      await navigator.clipboard.writeText(command);
      setCopiedCommandKey(commandKey);

      setTimeout(() => {
        setCopiedCommandKey("");
      }, 1500);
    } catch (error) {
      console.error("Copy command failed.", error);
      setOperationError("Command could not be copied. Please copy it manually.");
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
          {injectedErrors.map((error) => (
            <div className="list-item" key={`${error.code}-${error.device}`}>
              <strong>{error.code}</strong>
              <p>{error.description}</p>
              <p className="muted">
                {t("topic")}: {error.topic} | {t("device")}: {error.device} |{" "}
                {t("severity")}: {error.severity}
              </p>
            </div>
          ))}
        </div>

        <h4>{t("cliAccess")}</h4>
        <div className="result-list">
          {cliAccess.length === 0 && (
            <p className="muted">CLI access information is not available yet.</p>
          )}

          {cliAccess.map((cli, index) => {
            const dockerCommandKey = `${cli.deviceName}-docker-${index}`;
            const sshCommandKey = `${cli.deviceName}-ssh-${index}`;

            return (
              <div className="list-item" key={`${cli.deviceName}-${index}`}>
                <div className="result-title-row">
                  <strong>{cli.deviceName}</strong>
                  <span className="badge">CLI</span>
                </div>

                <p className="muted">
                  Container Name: {cli.containerName}
                </p>

                {cli.dockerExecCommand && (
                  <>
                    <p className="muted">Docker Exec Command:</p>
                    <code className="command-box">{cli.dockerExecCommand}</code>

                    <div className="actions">
                      <button
                        className="primary-button"
                        onClick={() =>
                          handleCopyCommand(
                            cli.dockerExecCommand,
                            dockerCommandKey
                          )
                        }
                      >
                        {copiedCommandKey === dockerCommandKey
                          ? "Copied"
                          : "Copy Docker Command"}
                      </button>
                    </div>
                  </>
                )}

                {cli.sshCommand && (
                  <>
                    <p className="muted">SSH Command:</p>
                    <code className="command-box">{cli.sshCommand}</code>

                    <div className="actions">
                      <button
                        className="primary-button"
                        onClick={() =>
                          handleCopyCommand(cli.sshCommand, sshCommandKey)
                        }
                      >
                        {copiedCommandKey === sshCommandKey
                          ? "Copied"
                          : "Copy SSH Command"}
                      </button>
                    </div>
                  </>
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
          <div className="result-list">
            <div className="list-item">
              <strong>Operation failed</strong>
              <p>{operationError}</p>
            </div>
          </div>
        )}

        {operationResult && (
          <div className="result-list">
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