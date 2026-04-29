import { useMemo, useState } from "react";
import { createSession } from "../services/apiService";
import MessageBox from "../components/MessageBox";

const difficultyDetails = {
  Easy: {
    expectedErrors: "2 basic errors",
    description:
      "Recommended for first-time users. Focuses on simple VLAN or IP configuration mistakes."
  },
  Medium: {
    expectedErrors: "3 moderate errors",
    description:
      "Includes multiple troubleshooting steps such as VLAN, trunk, and connectivity checks."
  },
  Hard: {
    expectedErrors: "5 complex errors",
    description:
      "Designed for advanced practice with multiple dependent configuration problems."
  }
};

function CreateLab({ onSessionCreated }) {
  const [difficulty, setDifficulty] = useState("Easy");
  const [isCreating, setIsCreating] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const selectedDifficulty = useMemo(() => {
    return difficultyDetails[difficulty];
  }, [difficulty]);

  async function handleCreateSession() {
    setIsCreating(true);
    setErrorMessage("");

    try {
      const newSession = await createSession(difficulty);
      onSessionCreated(newSession);
    } catch (error) {
      setErrorMessage("Session could not be created. Please try again.");
      console.error(error);
    } finally {
      setIsCreating(false);
    }
  }

  return (
    <div className="two-column">
      <section className="card">
        <h2>Create Lab / Laboratuvar Oluştur</h2>

        <p className="muted">
          Select a difficulty level. In the real system, this choice will affect
          topology generation and injected errors.
        </p>

        {errorMessage && (
          <MessageBox
            type="error"
            title="Session creation failed"
            message={errorMessage}
          />
        )}

        <div className="form-group">
          <label htmlFor="difficulty">Difficulty / Zorluk</label>
          <select
            id="difficulty"
            value={difficulty}
            onChange={(event) => setDifficulty(event.target.value)}
          >
            <option value="Easy">Easy / Kolay</option>
            <option value="Medium">Medium / Orta</option>
            <option value="Hard">Hard / Zor</option>
          </select>
        </div>

        <button
          className="primary-button"
          onClick={handleCreateSession}
          disabled={isCreating}
        >
          {isCreating ? "Creating..." : "Create Session"}
        </button>

        <p className="footer-note">
          Note: This page currently uses mock data. Later, it will call the
          backend API through createSession().
        </p>
      </section>

      <section className="card">
        <h3>Difficulty Preview / Zorluk Önizlemesi</h3>

        <span className={`badge ${difficulty.toLowerCase()}`}>
          {difficulty}
        </span>

        <div className="info-row">
          <span>Expected Errors</span>
          <strong>{selectedDifficulty.expectedErrors}</strong>
        </div>

        <p>{selectedDifficulty.description}</p>

        <ul className="list">
          <li>Topology will be selected based on difficulty.</li>
          <li>Error injection rules will use this difficulty value.</li>
          <li>Validation score will depend on fixed and remaining errors.</li>
        </ul>
      </section>
    </div>
  );
}

export default CreateLab;