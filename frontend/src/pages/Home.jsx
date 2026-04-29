import StatCard from "../components/StatCard";

function Home({ session, onNavigate }) {
  return (
    <>
      <section className="hero">
        <h2>AutoNetLab Dashboard</h2>
        <p>
          This dashboard helps students create virtual network labs, view session
          information, inspect topology details, run validation, and receive
          learning recommendations.
        </p>

        <div className="actions">
          <button className="primary-button" onClick={() => onNavigate("create")}>
            Create New Lab
          </button>

          <button className="secondary-button" onClick={() => onNavigate("session")}>
            View Current Session
          </button>
        </div>
      </section>

      <section className="grid">
        <StatCard
          title="Current Session"
          value={session?.sessionId || "-"}
          helper="Active lab session identifier"
        />

        <StatCard
          title="Difficulty"
          value={session?.difficulty || "-"}
          helper="Selected lab difficulty level"
        />

        <StatCard
          title="Status"
          value={session?.status || "-"}
          helper="Current session status"
        />

        <StatCard
          title="Progress"
          value={`${session?.progress ?? 0}%`}
          helper="Mock progress value for demo"
        />
      </section>
    </>
  );
}

export default Home;