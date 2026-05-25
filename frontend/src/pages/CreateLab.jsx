import { useEffect, useMemo, useState } from "react";
import {
  createLab,
  getDifficulties,
  getErrorDetails,
  getErrorMessage,
  getLab
} from "../services/apiService";
import MessageBox from "../components/MessageBox";
import { useLanguage } from "../hooks/useLanguage";
import {
  formatDifficulty,
  getDifficultyClass
} from "../utils/formatters";

const HIDDEN_TOPOLOGY_TEMPLATE = "basic-two-router";

const DIFFICULTY_PREVIEWS = {
  easy: {
    title: "Guided fundamentals",
    topology: "2 devices / 1 link",
    summary: "A focused entry-level troubleshooting scenario for addressing and direct connectivity.",
    topics: ["IP addressing", "Interface status", "Basic connectivity"]
  },
  medium: {
    title: "Multi-topic practice",
    topology: "2 devices / 1 link",
    summary: "A broader scenario that combines multiple checks and requires more careful troubleshooting.",
    topics: ["Addressing", "Routing basics", "Connectivity validation"]
  },
  hard: {
    title: "Advanced ring challenge",
    topology: "4 devices / 4 links",
    summary: "A four-device ring topology designed for deeper routing, interface, and connectivity analysis.",
    topics: ["Static routing", "Interface status", "End-to-end connectivity", "Multi-device reasoning"]
  }
};

function getSignedInStudentId(authUser) {
  return (
    authUser?.student_id ||
    authUser?.studentId ||
    authUser?.username ||
    "student"
  );
}

function normalizeDifficulties(items) {
  if (!Array.isArray(items) || items.length === 0) {
    return [
      { value: "easy", label: "Easy" },
      { value: "medium", label: "Medium" },
      { value: "hard", label: "Hard" }
    ];
  }

  return items;
}

function CreateLab({ authUser, onLabCreated, onNavigate }) {
  const { t } = useLanguage();

  const signedInStudentId = getSignedInStudentId(authUser);

  const [difficulty, setDifficulty] = useState("easy");
  const [difficulties, setDifficulties] = useState([]);
  const [isCreating, setIsCreating] = useState(false);
  const [isOpeningActiveLab, setIsOpeningActiveLab] = useState(false);
  const [activeLabConflict, setActiveLabConflict] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [errorDetails, setErrorDetails] = useState("");

  useEffect(() => {
    async function loadDifficulties() {
      try {
        const data = await getDifficulties();
        setDifficulties(normalizeDifficulties(data.difficulties));
      } catch (error) {
        setDifficulties(normalizeDifficulties([]));
        setErrorMessage("Difficulty options could not be loaded. Default options are being shown.");
        setErrorDetails(getErrorDetails(error));
        console.error(error);
      }
    }

    loadDifficulties();
  }, []);

  const selectedDifficulty = useMemo(() => {
    return difficulties.find((item) => item.value === difficulty);
  }, [difficulty, difficulties]);

  const selectedPreview = DIFFICULTY_PREVIEWS[difficulty] || DIFFICULTY_PREVIEWS.easy;

  async function handleCreateLab() {
    setIsCreating(true);
    setErrorMessage("");
    setErrorDetails("");
    setActiveLabConflict(null);

    try {
      const newLab = await createLab({
        student_id: signedInStudentId,
        difficulty,
        topology_template: HIDDEN_TOPOLOGY_TEMPLATE
      });

      onLabCreated(newLab);
    } catch (error) {
      const isActiveLabConflict =
        error?.errorCode === "ACTIVE_LAB_ALREADY_EXISTS" ||
        Boolean(error?.activeSessionId);

      if (isActiveLabConflict) {
        setActiveLabConflict({
          sessionId: error.activeSessionId || "",
          message:
            error.friendlyMessage ||
            "You already have an active lab. Finish or close it before creating a new one."
        });
      }

      setErrorMessage(getErrorMessage(error, "Lab could not be created. Please try again."));
      setErrorDetails(getErrorDetails(error));
      console.error(error);
    } finally {
      setIsCreating(false);
    }
  }

  async function handleOpenActiveLab() {
    if (!activeLabConflict?.sessionId) {
      onNavigate("myLabs");
      return;
    }

    setIsOpeningActiveLab(true);
    setErrorMessage("");
    setErrorDetails("");

    try {
      const activeLab = await getLab(activeLabConflict.sessionId);
      onLabCreated(activeLab);
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Active lab could not be opened."));
      setErrorDetails(getErrorDetails(error));
      console.error(error);
    } finally {
      setIsOpeningActiveLab(false);
    }
  }

  return (
    <div className="create-lab-page">
      <section className="card create-lab-main-card">
        <div className="section-title-row">
          <div>
            <h2>Create Lab</h2>
            <p className="muted">
              Select a difficulty level to generate a troubleshooting scenario.
              The lab session will open in your workspace. Start the environment there when you are ready.
            </p>
          </div>

          <div className="signed-in-summary">
            <span>Signed-in student</span>
            <strong>{authUser?.display_name || authUser?.username || "Student"}</strong>
            <small>{signedInStudentId}</small>
          </div>
        </div>

        {errorMessage && (
          <>
            <MessageBox
              type="error"
              title={activeLabConflict ? "Active lab already exists" : "Lab creation failed"}
              message={
                activeLabConflict
                  ? "You already have an active lab. Open the active lab or finish it from My Labs before creating a new one."
                  : errorMessage
              }
            />

            {activeLabConflict && (
              <div className="actions">
                <button
                  className="primary-button"
                  type="button"
                  onClick={handleOpenActiveLab}
                  disabled={isOpeningActiveLab}
                >
                  {isOpeningActiveLab ? "Opening..." : "Open Active Lab"}
                </button>

                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => onNavigate("myLabs")}
                >
                  View My Labs
                </button>
              </div>
            )}

            {errorDetails && (
              <details className="technical-detail-box">
                <summary>Show diagnostics</summary>
                <p>{errorDetails}</p>
              </details>
            )}
          </>
        )}

        <div className="difficulty-card-grid" role="radiogroup" aria-label="Lab difficulty">
          {difficulties.map((item) => {
            const preview = DIFFICULTY_PREVIEWS[item.value] || {
              title: item.label || formatDifficulty(item.value, t),
              topology: "Topology generated by difficulty",
              summary: item.description || "Troubleshooting scenario generated by AutoNetLab.",
              topics: ["Troubleshooting", "Validation"]
            };
            const isSelected = difficulty === item.value;

            return (
              <button
                key={item.value}
                className={`difficulty-select-card ${isSelected ? "selected" : ""}`}
                type="button"
                role="radio"
                aria-checked={isSelected}
                onClick={() => setDifficulty(item.value)}
              >
                <span className={`badge ${getDifficultyClass(item.value)}`}>
                  {formatDifficulty(item.value, t)}
                </span>
                <strong>{preview.title}</strong>
                <small>{preview.topology}</small>
                <p>{preview.summary}</p>
              </button>
            );
          })}
        </div>

        <div className="actions create-lab-actions">
          <button
            className="primary-button"
            onClick={handleCreateLab}
            disabled={isCreating}
            type="button"
          >
            {isCreating ? "Creating Lab..." : "Create Lab"}
          </button>

          <button
            className="secondary-button"
            onClick={() => onNavigate("myLabs")}
            type="button"
          >
            View My Labs
          </button>
        </div>
      </section>

      <section className="card create-lab-preview-card">
        <span className={`badge ${getDifficultyClass(difficulty)}`}>
          {formatDifficulty(difficulty, t)}
        </span>

        <h3>{selectedPreview.title}</h3>
        <p className="muted">
          {selectedDifficulty?.description || selectedPreview.summary}
        </p>

        <div className="info-row">
          <span>Topology</span>
          <strong>{selectedPreview.topology}</strong>
        </div>

        <div className="info-row">
          <span>Workspace</span>
          <strong>Web CLI + topology view</strong>
        </div>

        <div className="info-row">
          <span>Validation</span>
          <strong>Score and recommendations</strong>
        </div>

        <h4>Practice topics</h4>
        <ul className="list">
          {selectedPreview.topics.map((topic) => (
            <li key={topic}>{topic}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}

export default CreateLab;

