import StatCard from "../components/StatCard";
import MessageBox from "../components/MessageBox";
import { useLanguage } from "../hooks/useLanguage";
import {
  formatDifficulty,
  formatStatus
} from "../utils/formatters";

function getNormalizedStatus(status) {
  return String(status || "").toLowerCase();
}

function hasValidationSignal(labSession) {
  return (
    labSession?.passed === true ||
    labSession?.passed === false ||
    labSession?.score !== null && labSession?.score !== undefined ||
    labSession?.fault_resolution_score !== null && labSession?.fault_resolution_score !== undefined
  );
}

function isWorkspaceOpenable(labSession) {
  if (!labSession?.session_id) {
    return false;
  }

  const status = getNormalizedStatus(labSession.status);

  if (["created", "deployed", "active", "error"].includes(status)) {
    return true;
  }

  if (status === "validated") {
    return labSession.passed !== true;
  }

  return false;
}

function getScenarioTitle(labSession) {
  return (
    labSession?.scenario?.title ||
    labSession?.scenario_title ||
    labSession?.scenarioTitle ||
    labSession?.scenario_name ||
    labSession?.scenarioName ||
    labSession?.topology?.scenario_title ||
    labSession?.scenario_id ||
    labSession?.scenarioId ||
    ""
  );
}

function getCurrentLabValue(labSession) {
  if (!labSession?.session_id) {
    return "-";
  }

  const scenarioTitle = getScenarioTitle(labSession);

  if (!scenarioTitle) {
    return labSession.session_id;
  }

  return `${scenarioTitle} · ${labSession.session_id}`;
}

function getNextStep(labSession) {
  if (!labSession?.session_id) {
    return {
      value: "Create Lab",
      helper: "Start a new lab session to generate a topology."
    };
  }

  const status = getNormalizedStatus(labSession.status);

  if (status === "error") {
    return {
      value: "Cleanup Required",
      helper: "Open the workspace and cleanup the errored runtime before starting a new lab."
    };
  }

  if (["created", "deployed", "active"].includes(status)) {
    return {
      value: "Open Workspace",
      helper: "Continue deployment, troubleshooting, or validation from the workspace."
    };
  }

  if (status === "validated" && labSession.passed === false) {
    return {
      value: "Continue Troubleshooting",
      helper: "Return to the workspace, update the live configuration, and run validation again."
    };
  }

  if (status === "validated" && labSession.passed === true) {
    return {
      value: "Review Results or Create New Lab",
      helper: "Review the passed validation result, finish the lab, or start another scenario."
    };
  }

  if (status === "finished" && labSession.passed === false) {
    return {
      value: "Review Results or Create New Lab",
      helper: "Review the saved result from My Labs or start a new lab."
    };
  }

  if (status === "finished" || status === "destroyed") {
    return {
      value: "Create New Lab",
      helper: "This lab is no longer running. Start a new lab when you are ready."
    };
  }

  if (hasValidationSignal(labSession)) {
    return {
      value: "Review Results",
      helper: "Open the saved validation result from My Labs."
    };
  }

  return {
    value: isWorkspaceOpenable(labSession) ? "Open Workspace" : "Create Lab",
    helper: isWorkspaceOpenable(labSession)
      ? "Continue this lab from the workspace."
      : "Start a new lab session to continue training."
  };
}

function Home({ labSession, onNavigate }) {
  const { t } = useLanguage();

  const hasLabSession = Boolean(labSession?.session_id);
  const canOpenWorkspace = isWorkspaceOpenable(labSession);
  const canReviewResult = hasLabSession && hasValidationSignal(labSession);
  const nextStep = getNextStep(labSession);

  return (
    <>
      <section className="hero student-home-hero">
        <div className="hero-copy">
          <h2>{t("dashboardTitle")}</h2>
          <p>
            Create troubleshooting labs, inspect the generated topology, connect
            to devices through the Web CLI, validate your solution, and review
            recommendations from one guided workspace.
          </p>
        </div>

        <div className="actions hero-actions">
          <button className="primary-button" onClick={() => onNavigate("create")}>
            Create New Lab
          </button>

          <button className="secondary-button" onClick={() => onNavigate("myLabs")}>
            View My Labs
          </button>

          {canOpenWorkspace && (
            <button className="secondary-button" onClick={() => onNavigate("workspace")}>
              Continue Workspace
            </button>
          )}

          {!canOpenWorkspace && canReviewResult && (
            <button className="secondary-button" onClick={() => onNavigate("result")}>
              Review Results
            </button>
          )}
        </div>
      </section>

      {!hasLabSession && (
        <MessageBox
          type="info"
          title="No restorable lab session"
          message="Create a lab or open a previous session from My Labs to begin troubleshooting."
        />
      )}

      {hasLabSession && !canOpenWorkspace && (
        <MessageBox
          type="info"
          title="Latest lab is not running"
          message="A recent lab result is available. You can review the result from this page or start a new lab."
        />
      )}

      <section className="grid student-home-grid">
        <StatCard
          title="Current Lab"
          value={getCurrentLabValue(labSession)}
          helper={
            hasLabSession
              ? "The latest selected or restored lab session."
              : "No lab session is currently selected."
          }
        />

        <StatCard
          title="Difficulty"
          value={formatDifficulty(labSession?.difficulty, t)}
          helper="The troubleshooting level selected for this lab."
        />

        <StatCard
          title="Status"
          value={formatStatus(labSession?.status, t)}
          helper="The current lifecycle state of the selected lab."
        />

        <StatCard
          title="Next Step"
          value={nextStep.value}
          helper={nextStep.helper}
        />
      </section>
    </>
  );
}

export default Home;

