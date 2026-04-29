import { useEffect, useMemo, useState } from "react";
import { createLab, getDifficulties } from "../services/apiService";
import MessageBox from "../components/MessageBox";
import { useLanguage } from "../hooks/useLanguage";
import {
  formatDifficulty,
  getDifficultyClass
} from "../utils/formatters";

function CreateLab({ onLabCreated }) {
  const { t } = useLanguage();

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
        setErrorMessage(t("difficultyOptionsFailed"));
        console.error(error);
      }
    }

    loadDifficulties();
  }, [t]);

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
      setErrorMessage(t("labCreationFailedMessage"));
      console.error(error);
    } finally {
      setIsCreating(false);
    }
  }

  return (
    <div className="two-column">
      <section className="card">
        <h2>{t("createLabTitle")}</h2>

        <p className="muted">{t("createLabDescription")}</p>

        {errorMessage && (
          <MessageBox
            type="error"
            title={t("labCreationFailed")}
            message={errorMessage}
          />
        )}

        <div className="form-group">
          <label htmlFor="studentId">{t("studentId")}</label>
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
          <label htmlFor="difficulty">{t("difficulty")}</label>
          <select
            id="difficulty"
            value={difficulty}
            onChange={(event) => setDifficulty(event.target.value)}
          >
            {difficulties.map((item) => (
              <option key={item.value} value={item.value}>
                {formatDifficulty(item.value, t)}
              </option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="topologyTemplate">{t("topologyTemplate")}</label>
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
          {isCreating ? t("creating") : t("createLabButton")}
        </button>

        <p className="footer-note">{t("createLabNote")}</p>
      </section>

      <section className="card">
        <h3>{t("difficultyPreview")}</h3>

        <span className={`badge ${getDifficultyClass(difficulty)}`}>
          {formatDifficulty(difficulty, t)}
        </span>

        <div className="info-row">
          <span>{t("backendValue")}</span>
          <strong>{difficulty}</strong>
        </div>

        <p>
          {selectedDifficulty?.description || t("difficultyLoading")}
        </p>

        <ul className="list">
          <li>{t("easyCreates")}</li>
          <li>{t("mediumCreates")}</li>
          <li>{t("hardCreates")}</li>
        </ul>
      </section>
    </div>
  );
}

export default CreateLab;