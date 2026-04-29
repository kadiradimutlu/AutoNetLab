import TopologyCard from "../components/TopologyCard";
import {
  formatDifficulty,
  formatStatus,
  formatStudentName,
  getDifficultyClass
} from "../utils/formatters";

function SessionDetail({ labSession, onNavigate }) {
  if (!labSession) {
    return (
      <section className="card">
        <h2>Lab Session Detail / Lab Oturum Detayı</h2>
        <p className="muted">Lab session data is loading...</p>
      </section>
    );
  }

  const difficultyClass = getDifficultyClass(labSession.difficulty);

  return (
    <div className="two-column">
      <section className="card">
        <h2>Lab Session Detail / Lab Oturum Detayı</h2>

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
            {formatDifficulty(labSession.difficulty)}
          </span>
        </div>

        <div className="info-row">
          <span>Status</span>
          <strong>{formatStatus(labSession.status)}</strong>
        </div>

        <div className="info-row">
          <span>Injected Errors</span>
          <strong>{labSession.injected_errors.length}</strong>
        </div>

        <h4>Injected Errors / Eklenen Hatalar</h4>
        <div className="result-list">
          {labSession.injected_errors.map((error) => (
            <div className="list-item" key={`${error.code}-${error.device}`}>
              <strong>{error.code}</strong>
              <p>{error.description}</p>
              <p className="muted">
                Topic: {error.topic} | Device: {error.device} | Severity:{" "}
                {error.severity}
              </p>
            </div>
          ))}
        </div>

        <h4>CLI Access / CLI Erişimi</h4>
        <div className="result-list">
          {labSession.cli_access.map((cli) => (
            <div className="list-item" key={cli.device_id}>
              <strong>{cli.device_id}</strong>
              <p className="muted">{cli.command}</p>
            </div>
          ))}
        </div>

        <div className="actions">
          <button className="primary-button" onClick={() => onNavigate("result")}>
            Validate Lab
          </button>
        </div>

        <p className="footer-note">
          This screen now follows the backend lab session response format.
        </p>
      </section>

      <TopologyCard topology={labSession.topology} />
    </div>
  );
}

export default SessionDetail;