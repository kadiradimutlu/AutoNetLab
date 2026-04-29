import StatCard from "../components/StatCard";
import MessageBox from "../components/MessageBox";
import {
  formatDifficulty,
  formatStatus
} from "../utils/formatters";

function Home({ labSession, onNavigate }) {
  return (
    <>
      <section className="hero">
        <h2>AutoNetLab Dashboard</h2>
        <p>
          This dashboard helps students create virtual network labs, view lab
          session information, inspect topology details, run validation, and
          receive learning recommendations.
        </p>

        <div className="actions">
          <button className="primary-button" onClick={() => onNavigate("create")}>
            Create New Lab
          </button>

          <button className="secondary-button" onClick={() => onNavigate("session")}>
            View Current Lab
          </button>
        </div>
      </section>

      {!labSession && (
        <MessageBox
          type="info"
          title="Loading lab data"
          message="The dashboard is loading the current mock lab session information."
        />
      )}

      <section className="grid">
        <StatCard
          title="Current Lab"
          value={labSession?.session_id || "-"}
          helper="Active lab session identifier"
        />

        <StatCard
          title="Difficulty"
          value={formatDifficulty(labSession?.difficulty)}
          helper="Selected lab difficulty level"
        />

        <StatCard
          title="Status"
          value={formatStatus(labSession?.status)}
          helper="Current lab session status"
        />

        <StatCard
          title="Injected Errors"
          value={labSession?.injected_errors?.length ?? 0}
          helper="Number of generated troubleshooting errors"
        />
      </section>
    </>
  );
}

export default Home;