import { useState } from "react";
import { createSession } from "../services/apiService";

function CreateLab({ onSessionCreated }) {
  const [difficulty, setDifficulty] = useState("Easy");
  const [isCreating, setIsCreating] = useState(false);

  async function handleCreateSession() {
    setIsCreating(true);

    try {
      const newSession = await createSession(difficulty);
      onSessionCreated(newSession);
    } catch (error) {
      alert("Session could not be created.");
      console.error(error);
    } finally {
      setIsCreating(false);
    }
  }

  return (
    <section className="card">
      <h2>Create Lab / Laboratuvar Oluştur</h2>

      <p className="muted">
        Select a difficulty level. In the real system, this choice will affect
        topology generation and injected errors.
      </p>

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
        Note: This page currently uses mock data. Later, it will call the backend
        API through createSession().
      </p>
    </section>
  );
}

export default CreateLab;