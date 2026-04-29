import TopologyCard from "../components/TopologyCard";

function SessionDetail({ session, topology, onNavigate }) {
  if (!session) {
    return (
      <section className="card">
        <h2>Session Detail / Oturum Detayı</h2>
        <p className="muted">Session data is loading...</p>
      </section>
    );
  }

  const difficultyClass = session.difficulty.toLowerCase();

  return (
    <div className="two-column">
      <section className="card">
        <h2>Session Detail / Oturum Detayı</h2>

        <div className="info-row">
          <span>Session ID</span>
          <strong>{session.sessionId}</strong>
        </div>

        <div className="info-row">
          <span>User</span>
          <strong>{session.user.name}</strong>
        </div>

        <div className="info-row">
          <span>Lab Title</span>
          <strong>{session.labTitle}</strong>
        </div>

        <div className="info-row">
          <span>Difficulty</span>
          <span className={`badge ${difficultyClass}`}>
            {session.difficulty}
          </span>
        </div>

        <div className="info-row">
          <span>Status</span>
          <strong>{session.status}</strong>
        </div>

        <div className="info-row">
          <span>Progress</span>
          <strong>{session.progress}%</strong>
        </div>

        <div className="actions">
          <button className="primary-button" onClick={() => onNavigate("result")}>
            Validate Session
          </button>
        </div>

        <p className="footer-note">
          CLI interaction will happen outside the dashboard. This screen only
          displays session state and topology information.
        </p>
      </section>

      <TopologyCard topology={topology} />
    </div>
  );
}

export default SessionDetail;