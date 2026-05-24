import StatCard from "../components/StatCard";
import MessageBox from "../components/MessageBox";
import { useLanguage } from "../hooks/useLanguage";
import {
  formatDifficulty,
  formatStatus
} from "../utils/formatters";

function Home({ labSession, onNavigate }) {
  const { t } = useLanguage();

  const hasActiveLab = Boolean(labSession?.session_id);

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

          {hasActiveLab && (
            <button className="secondary-button" onClick={() => onNavigate("workspace")}>
              Continue Workspace
            </button>
          )}
        </div>
      </section>

      {!hasActiveLab && (
        <MessageBox
          type="info"
          title="No active lab session"
          message="Create a lab or open a previous session from My Labs to begin troubleshooting."
        />
      )}

      <section className="grid student-home-grid">
        <StatCard
          title="Current Lab"
          value={labSession?.session_id || "-"}
          helper="The lab session currently selected in your workspace."
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
          value={hasActiveLab ? "Open Workspace" : "Create Lab"}
          helper={
            hasActiveLab
              ? "Continue troubleshooting, validation, or cleanup from the workspace."
              : "Start a new lab session to generate a topology."
          }
        />
      </section>
    </>
  );
}

export default Home;

