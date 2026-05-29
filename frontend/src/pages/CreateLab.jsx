import { useEffect, useMemo, useState } from "react";
import {
  createLab,
  getDifficulties,
  getErrorDetails,
  getErrorMessage,
  getLab,
  getScenarios
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

function normalizeScenarios(items) {
  if (!Array.isArray(items)) {
    return [];
  }

  return items.filter((scenario) => scenario?.id);
}

function getScenarioDeviceCount(scenario) {
  return Array.isArray(scenario?.devices) ? scenario.devices.length : 0;
}

function getScenarioLinkCount(scenario) {
  if (Array.isArray(scenario?.links)) {
    return scenario.links.length;
  }

  if (Array.isArray(scenario?.addressing_table) && scenario.addressing_table.length >= 2) {
    return 1;
  }

  return 0;
}

function getScenarioCliSummary(scenario) {
  const profiles = new Set(
    (scenario?.devices || [])
      .map((device) => String(device?.cli_profile || device?.os || "").toLowerCase())
      .filter(Boolean)
  );

  if (profiles.has("sr_cli") && profiles.has("linux_shell")) {
    return "SR Linux CLI + Linux Shell";
  }

  if (profiles.size > 0) {
    return Array.from(profiles)
      .map((profile) => profile.replace(/_/g, " "))
      .join(" + ");
  }

  return "CLI access";
}

function getScenarioDisplaySummary(scenario) {
  return (
    scenario?.summary ||
    "Professional router-client lab using Nokia SR Linux and a Linux troubleshooting client."
  );
}

function CreateLab({ authUser, onLabCreated, onNavigate }) {
  const { t } = useLanguage();

  const signedInStudentId = getSignedInStudentId(authUser);

  const [difficulty, setDifficulty] = useState("easy");
  const [difficulties, setDifficulties] = useState([]);
  const [scenarios, setScenarios] = useState([]);
  const [selectedLabType, setSelectedLabType] = useState("classic");
  const [selectedScenarioId, setSelectedScenarioId] = useState("");
  const [isLoadingScenarios, setIsLoadingScenarios] = useState(false);
  const [scenarioLoadMessage, setScenarioLoadMessage] = useState("");
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

  useEffect(() => {
    let isMounted = true;

    async function loadScenarios() {
      setIsLoadingScenarios(true);
      setScenarioLoadMessage("");

      try {
        const data = await getScenarios();

        if (isMounted) {
          setScenarios(normalizeScenarios(data?.scenarios));
        }
      } catch (error) {
        console.error("Scenario catalog could not be loaded.", error);

        if (isMounted) {
          setScenarios([]);
          setSelectedLabType("classic");
          setSelectedScenarioId("");
          setScenarioLoadMessage(
            "Network realism scenarios could not be loaded. Classic troubleshooting labs are still available."
          );
        }
      } finally {
        if (isMounted) {
          setIsLoadingScenarios(false);
        }
      }
    }

    loadScenarios();

    return () => {
      isMounted = false;
    };
  }, []);

  const selectedDifficulty = useMemo(() => {
    return difficulties.find((item) => item.value === difficulty);
  }, [difficulty, difficulties]);

  const selectedPreview = DIFFICULTY_PREVIEWS[difficulty] || DIFFICULTY_PREVIEWS.easy;

  const selectedScenario = useMemo(() => {
    return scenarios.find((scenario) => scenario.id === selectedScenarioId) || null;
  }, [scenarios, selectedScenarioId]);

  const isScenarioMode = selectedLabType === "scenario" && Boolean(selectedScenarioId);

  function handleSelectClassicLab() {
    setSelectedLabType("classic");
    setSelectedScenarioId("");
  }

  function handleSelectScenario(scenarioId) {
    setSelectedLabType("scenario");
    setSelectedScenarioId(scenarioId);
  }

  async function handleCreateLab() {
    setIsCreating(true);
    setErrorMessage("");
    setErrorDetails("");
    setActiveLabConflict(null);

    try {
      const requestBody = {
        student_id: signedInStudentId,
        difficulty
      };

      if (isScenarioMode) {
        requestBody.scenario_id = selectedScenarioId;
      } else {
        requestBody.topology_template = HIDDEN_TOPOLOGY_TEMPLATE;
      }

      const newLab = await createLab(requestBody);

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
              Select a lab type and difficulty level to generate a troubleshooting scenario.
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
              title={activeLabConflict ? "Lab creation blocked" : "Lab creation failed"}
              message={
                errorMessage ||
                (activeLabConflict
                  ? "You already have an active or cleanup-required lab. Open My Labs and resolve it before creating a new one."
                  : "The lab could not be created.")
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

        <div className="lab-choice-section">
          <div className="section-title-row compact">
            <div>
              <h3>Choose Lab Type</h3>
              <p className="muted">
                Classic labs keep the existing AutoNetLab flow. Network realism scenarios use the new SR Linux backend contract.
              </p>
            </div>
          </div>

          {scenarioLoadMessage && (
            <MessageBox
              type="info"
              title="Scenario catalog unavailable"
              message={scenarioLoadMessage}
            />
          )}

          <div className="lab-type-grid" role="radiogroup" aria-label="Lab type">
            <button
              className={`lab-type-card ${selectedLabType === "classic" ? "selected" : ""}`}
              type="button"
              role="radio"
              aria-checked={selectedLabType === "classic"}
              onClick={handleSelectClassicLab}
            >
              <span className="badge neutral">Classic</span>
              <strong>Classic Troubleshooting Labs</strong>
              <p>
                Generate the existing AutoNetLab lab by difficulty. This keeps the current student flow, topology view, Web CLI, validation, and recommendations.
              </p>
              <small>Uses legacy topology template: {HIDDEN_TOPOLOGY_TEMPLATE}</small>
            </button>

            <div className="scenario-card-grid">
              {isLoadingScenarios && (
                <div className="lab-type-card scenario-select-card muted-card">
                  <span className="badge neutral">Loading</span>
                  <strong>Loading network realism scenarios...</strong>
                  <p>Classic labs remain available while the scenario catalog loads.</p>
                </div>
              )}

              {!isLoadingScenarios && scenarios.length === 0 && (
                <div className="lab-type-card scenario-select-card muted-card">
                  <span className="badge neutral">Network Realism</span>
                  <strong>No scenario catalog available</strong>
                  <p>Classic troubleshooting labs are still available.</p>
                </div>
              )}

              {!isLoadingScenarios && scenarios.map((scenario) => {
                const isSelected = selectedLabType === "scenario" && selectedScenarioId === scenario.id;

                return (
                  <button
                    className={`lab-type-card scenario-select-card ${isSelected ? "selected" : ""}`}
                    type="button"
                    role="radio"
                    aria-checked={isSelected}
                    key={scenario.id}
                    onClick={() => handleSelectScenario(scenario.id)}
                  >
                    <span className="badge neutral">Network Realism Scenario</span>
                    <strong>{scenario.title || scenario.id}</strong>
                    <p>{getScenarioDisplaySummary(scenario)}</p>

                    <div className="scenario-card-meta-grid">
                      <div>
                        <span>Router OS</span>
                        <strong>{scenario.router_os || "Nokia SR Linux"}</strong>
                      </div>

                      <div>
                        <span>Devices</span>
                        <strong>{getScenarioDeviceCount(scenario)}</strong>
                      </div>

                      <div>
                        <span>Links</span>
                        <strong>{getScenarioLinkCount(scenario)}</strong>
                      </div>

                      <div>
                        <span>CLI</span>
                        <strong>{getScenarioCliSummary(scenario)}</strong>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        <div className="lab-choice-section">
          <div className="section-title-row compact">
            <div>
              <h3>Choose Difficulty</h3>
              <p className="muted">
                Difficulty still controls the expected challenge level and validation behavior.
              </p>
            </div>
          </div>

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

        <h3>{isScenarioMode ? selectedScenario?.title || "Network Realism Scenario" : selectedPreview.title}</h3>
        <p className="muted">
          {isScenarioMode
            ? getScenarioDisplaySummary(selectedScenario)
            : selectedDifficulty?.description || selectedPreview.summary}
        </p>

        <div className="info-row">
          <span>Lab Type</span>
          <strong>{isScenarioMode ? "Network Realism Scenario" : "Classic Troubleshooting Lab"}</strong>
        </div>

        <div className="info-row">
          <span>Topology</span>
          <strong>
            {isScenarioMode
              ? selectedScenario?.topology_template || "srl-basic-link"
              : selectedPreview.topology}
          </strong>
        </div>

        <div className="info-row">
          <span>Workspace</span>
          <strong>Web CLI + topology view</strong>
        </div>

        <div className="info-row">
          <span>Validation</span>
          <strong>Score and recommendations</strong>
        </div>

        {isScenarioMode ? (
          <>
            <h4>Scenario requirements</h4>
            <ul className="list">
              {(selectedScenario?.student_tasks || [
                "Inspect the topology and identify device roles.",
                "Compare live state with the design requirements.",
                "Restore expected connectivity and run validation."
              ]).map((task) => (
                <li key={task}>{task}</li>
              ))}
            </ul>
          </>
        ) : (
          <>
            <h4>Practice topics</h4>
            <ul className="list">
              {selectedPreview.topics.map((topic) => (
                <li key={topic}>{topic}</li>
              ))}
            </ul>
          </>
        )}
      </section>
    </div>
  );
}

export default CreateLab;

