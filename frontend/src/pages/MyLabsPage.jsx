import { useEffect, useState } from "react";
import MessageBox from "../components/MessageBox";
import {
  destroyLab,
  finishLab,
  getErrorDetails,
  getErrorMessage,
  listLabSessions
} from "../services/apiService";
import { clearTerminalTranscriptsForSession } from "../utils/terminalTranscriptStorage";
import {
  formatDifficulty,
  formatStatus,
  getDifficultyClass
} from "../utils/formatters";

const ACTIVE_LAB_STATUSES = ["created", "deployed", "validated", "active"];
const CLEANUP_REQUIRED_STATUSES = ["error"];

function isActiveLabStatus(status) {
  return ACTIVE_LAB_STATUSES.includes(String(status || "").toLowerCase());
}

function isCleanupRequiredStatus(status) {
  return CLEANUP_REQUIRED_STATUSES.includes(String(status || "").toLowerCase());
}

function formatDateTime(value) {
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

function formatPassState(value) {
  if (value === true) {
    return "Passed";
  }

  if (value === false) {
    return "Needs work";
  }

  return "Not validated";
}

function getPassBadgeClass(value) {
  if (value === true) {
    return "pass";
  }

  if (value === false) {
    return "fail";
  }

  return "neutral";
}

function hasSavedValidationResult(session) {
  return (
    session?.score !== null &&
    session?.score !== undefined
  ) || session?.passed === true || session?.passed === false;
}

function getTopologySummary(session) {
  const summary = session?.topology_summary || {};

  return {
    name: summary.name || session?.topology?.name || "-",
    nodeCount: summary.node_count ?? summary.nodeCount ?? "-",
    linkCount: summary.link_count ?? summary.linkCount ?? "-",
    devices: Array.isArray(summary.devices) ? summary.devices : []
  };
}

function MyLabsPage({ authUser, onLabSelected, onNavigate }) {
  const [sessions, setSessions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedSessionId, setSelectedSessionId] = useState("");
  const [closingSessionId, setClosingSessionId] = useState("");
  const [cleanupSessionId, setCleanupSessionId] = useState("");
  const [infoMessage, setInfoMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [errorDetails, setErrorDetails] = useState("");

  async function loadLabs() {
    setIsLoading(true);
    setErrorMessage("");
    setErrorDetails("");

    try {
      const result = await listLabSessions({ limit: 50 });
      setSessions(Array.isArray(result?.sessions) ? result.sessions : []);
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Lab history could not be loaded."));
      setErrorDetails(getErrorDetails(error));
      console.error("Lab history could not be loaded.", error);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadLabs();
  }, []);

  async function handleOpenLab(session, targetPage) {
    setSelectedSessionId(session.session_id);
    setErrorMessage("");
    setErrorDetails("");

    try {
      await onLabSelected(session, targetPage);
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Selected lab could not be opened."));
      setErrorDetails(getErrorDetails(error));
      console.error("Selected lab could not be opened.", error);
    } finally {
      setSelectedSessionId("");
    }
  }

  async function handleCloseActiveLab(session) {
    if (!session?.session_id) {
      return;
    }

    const shouldClose = window.confirm(
      "Close this active lab? Running containers will be stopped, but validation history and results will be preserved."
    );

    if (!shouldClose) {
      return;
    }

    setClosingSessionId(session.session_id);
    setInfoMessage("");
    setErrorMessage("");
    setErrorDetails("");

    try {
      await finishLab(session.session_id);
      setInfoMessage("Active lab closed successfully. Validation history is preserved.");
      await loadLabs();
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Active lab could not be closed."));
      setErrorDetails(getErrorDetails(error));
      console.error("Active lab close failed.", error);
    } finally {
      setClosingSessionId("");
    }
  }

  async function handleCleanupErroredLab(session) {
    if (!session?.session_id) {
      return;
    }

    const shouldCleanup = window.confirm(
      "Cleanup this errored lab runtime? Any remaining containers will be removed. Validation history and saved results will be preserved."
    );

    if (!shouldCleanup) {
      return;
    }

    setCleanupSessionId(session.session_id);
    setInfoMessage("");
    setErrorMessage("");
    setErrorDetails("");

    try {
      await destroyLab(session.session_id);
      clearTerminalTranscriptsForSession(session.session_id);
      setInfoMessage("Lab runtime cleanup completed. The session history is preserved.");
      await loadLabs();
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Lab runtime cleanup could not be completed."));
      setErrorDetails(getErrorDetails(error));
      console.error("Lab runtime cleanup failed.", error);
    } finally {
      setCleanupSessionId("");
    }
  }

  return (
    <section className="my-labs-page">
      <div className="section-title-row">
        <div>
          <h2>My Labs</h2>
          <p className="muted">
            Review your lab history, open workspaces, and view saved validation results.
          </p>
        </div>

        <div className="actions">
          <button className="secondary-button" type="button" onClick={loadLabs}>
            Refresh
          </button>

          <button className="primary-button" type="button" onClick={() => onNavigate("create")}>
            Create New Lab
          </button>
        </div>
      </div>

      <section className="grid my-labs-summary-grid">
        <div className="stat-card">
          <span>Total labs</span>
          <strong>{sessions.length}</strong>
          <small>Visible for {authUser?.display_name || authUser?.username || "the signed-in user"}</small>
        </div>

        <div className="stat-card">
          <span>Active labs</span>
          <strong>
            {sessions.filter((session) => isActiveLabStatus(session.status)).length}
          </strong>
          <small>Created, deployed, or validated sessions</small>
        </div>

        <div className="stat-card">
          <span>Validated labs</span>
          <strong>
            {sessions.filter((session) => hasSavedValidationResult(session)).length}
          </strong>
          <small>Sessions with scoring data</small>
        </div>

        <div className="stat-card">
          <span>Needs cleanup</span>
          <strong>
            {sessions.filter((session) => isCleanupRequiredStatus(session.status)).length}
          </strong>
          <small>Error-state sessions that may need runtime cleanup</small>
        </div>

        <div className="stat-card">
          <span>Passed labs</span>
          <strong>{sessions.filter((session) => session.passed === true).length}</strong>
          <small>Successful validation results</small>
        </div>
      </section>

      {infoMessage && (
        <MessageBox
          type="success"
          title="Lab updated"
          message={infoMessage}
        />
      )}

      {errorMessage && (
        <>
          <MessageBox
            type="error"
            title="Lab history error"
            message={errorMessage}
          />

          {errorDetails && (
            <div className="technical-detail-box">
              <strong>Diagnostics</strong>
              <p>{errorDetails}</p>
            </div>
          )}
        </>
      )}

      {isLoading && (
        <section className="card">
          <h3>Loading lab history...</h3>
          <p className="muted">Loading your saved lab sessions and recent troubleshooting history.</p>
        </section>
      )}

      {!isLoading && sessions.length === 0 && !errorMessage && (
        <MessageBox
          type="info"
          title="No labs found"
          message="Create your first lab to populate this history page."
        />
      )}

      {!isLoading && sessions.length > 0 && (
        <div className="my-labs-list">
          {sessions.map((session) => {
            const topologySummary = getTopologySummary(session);
            const difficultyClass = getDifficultyClass(session.difficulty);
            const passBadgeClass = getPassBadgeClass(session.passed);
            const isSelected = selectedSessionId === session.session_id;
            const isClosing = closingSessionId === session.session_id;
            const isCleaning = cleanupSessionId === session.session_id;
            const isActive = isActiveLabStatus(session.status);
            const needsCleanup = isCleanupRequiredStatus(session.status);
            const hasResults = hasSavedValidationResult(session);
            const isBusy = isSelected || isClosing || isCleaning;

            return (
              <article className="card my-lab-card" key={session.session_id}>
                <div className="my-lab-card-header">
                  <div>
                    <h3>{session.session_id}</h3>
                    <p className="muted">
                      {topologySummary.name} / {topologySummary.nodeCount} devices / {topologySummary.linkCount} links
                    </p>
                  </div>

                  <div className="my-lab-badges">
                    <span className={`badge ${difficultyClass}`}>
                      {formatDifficulty(session.difficulty)}
                    </span>
                    <span className="badge neutral">
                      {formatStatus(session.status)}
                    </span>
                    <span className={`badge ${passBadgeClass}`}>
                      {formatPassState(session.passed)}
                    </span>
                  </div>
                </div>

                <div className="my-lab-detail-grid">
                  <div>
                    <span className="muted">Score</span>
                    <strong>{session.score ?? "-"}</strong>
                  </div>

                  <div>
                    <span className="muted">Created</span>
                    <strong>{formatDateTime(session.created_at)}</strong>
                  </div>

                  <div>
                    <span className="muted">Completed</span>
                    <strong>{formatDateTime(session.completed_at)}</strong>
                  </div>

                  <div>
                    <span className="muted">Devices</span>
                    <strong>
                      {topologySummary.devices.length > 0
                        ? topologySummary.devices.join(", ")
                        : "-"}
                    </strong>
                  </div>
                </div>

                {isActive && (
                  <MessageBox
                    type="info"
                    title="Active lab"
                    message="This lab can still be opened. Close it when you no longer need the running containers."
                  />
                )}

                {needsCleanup && (
                  <MessageBox
                    type="error"
                    title="Runtime cleanup required"
                    message="This lab entered an error state. Cleanup Runtime removes any remaining containers while preserving the session history."
                  />
                )}

                <div className="actions">
                  <button
                    className="primary-button"
                    type="button"
                    onClick={() => handleOpenLab(session, "workspace")}
                    disabled={isBusy}
                  >
                    {isSelected ? "Opening..." : "Open Workspace"}
                  </button>

                  {hasResults && (
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() => handleOpenLab(session, "result")}
                      disabled={isBusy}
                    >
                      {isSelected ? "Opening..." : "View Results"}
                    </button>
                  )}

                  {isActive && (
                    <button
                      className="danger-button"
                      type="button"
                      onClick={() => handleCloseActiveLab(session)}
                      disabled={isBusy}
                    >
                      {isClosing ? "Closing..." : "Close Active Lab"}
                    </button>
                  )}

                  {needsCleanup && (
                    <button
                      className="danger-button"
                      type="button"
                      onClick={() => handleCleanupErroredLab(session)}
                      disabled={isBusy}
                    >
                      {isCleaning ? "Cleaning..." : "Cleanup Runtime"}
                    </button>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}

export default MyLabsPage;

