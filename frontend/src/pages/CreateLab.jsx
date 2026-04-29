import { useEffect, useMemo, useState } from "react";
import { createLab, getDifficulties } from "../services/apiService";
import MessageBox from "../components/MessageBox";
import {
  formatDifficulty,
  getDifficultyClass
} from "../utils/formatters";

function CreateLab({ onLabCreated }) {
  const [studentId, setStudentId] = useState("muhammed");
  const [difficulty, setDifficulty] = useState("easy");
  const [topologyTemplate, setTopologyTemplate] = useState("basic-two-router");
  const [difficulties, setDifficulties] = useState([]);
  const [isCreating, setIsCreating] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    async function loadDifficulties() {
      try {
        const data = await getDifficulties();
        setDifficulties(data.difficulties);
      } catch (error) {
        setErrorMessage("Difficulty options could not be loaded.");
        console.error(error);
      }
    }

    loadDifficulties();
  }, []);

  const selectedDifficulty = useMemo(() => {
    return difficulties.find((item) => item.value === difficulty);
  }, [difficulty, difficulties]);

  async function handleCreateLab() {
    setIsCreating(true);
    setErrorMessage("");

    try {
      const newLab = await createLab({
        student_id: studentId,
        difficulty,
        topology_template: topologyTemplate
      });

      onLabCreated(newLab);
    } catch (error) {
      setErrorMessage("Lab session could not be created. Please try again.");
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
          Select a difficulty level. This value will be sent to the backend as
          easy, medium, or hard.
        </p>

        {errorMessage && (
          <MessageBox
            type="error"
            title="Lab creation failed"
            message={errorMessage}
          />
        )}

        <div className="form-group">
          <label htmlFor="studentId">Student ID / Öğrenci</label>
          <select
            id="studentId"
            value={studentId}
            onChange={(event) => setStudentId(event.target.value)}
          >
            <option value="muhammed">Muhammed</option>
            <option value="kadir">Kadir</option>
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="difficulty">Difficulty / Zorluk</label>
          <select
            id="difficulty"
            value={difficulty}
            onChange={(event) => setDifficulty(event.target.value)}
          >
            {difficulties.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="topologyTemplate">Topology Template / Topoloji Şablonu</label>
          <select
            id="topologyTemplate"
            value={topologyTemplate}
            onChange={(event) => setTopologyTemplate(event.target.value)}
          >
            <option value="basic-two-router">basic-two-router</option>
          </select>
        </div>

        <button
          className="primary-button"
          onClick={handleCreateLab}
          disabled={isCreating}
        >
          {isCreating ? "Creating..." : "Create Lab"}
        </button>

        <p className="footer-note">
          Note: This page currently uses backend-compatible mock data. Later, it
          will call POST /api/labs.
        </p>
      </section>

      <section className="card">
        <h3>Difficulty Preview / Zorluk Önizlemesi</h3>

        <span className={`badge ${getDifficultyClass(difficulty)}`}>
          {formatDifficulty(difficulty)}
        </span>

        <div className="info-row">
          <span>Backend Value</span>
          <strong>{difficulty}</strong>
        </div>

        <p>
          {selectedDifficulty?.description ||
            "Difficulty description is loading..."}
        </p>

        <ul className="list">
          <li>Easy creates 2 injected errors.</li>
          <li>Medium creates 3 injected errors.</li>
          <li>Hard creates 5 injected errors.</li>
        </ul>
      </section>
    </div>
  );
}

export default CreateLab;