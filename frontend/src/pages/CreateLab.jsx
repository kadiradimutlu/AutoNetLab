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

const DEFAULT_SCENARIO_ID = "srl-basic-link";
const CAMPUS_SCENARIO_ID = "campus-core-static-routing";

const FALLBACK_SRL_SCENARIO = {
  id: DEFAULT_SCENARIO_ID,
  title: "SR Linux Basic Link Troubleshooting",
  summary: "A professional router-client starter scenario using Nokia SR Linux and a Linux client.",
  topology_template: "srl-basic-link",
  router_os: "Nokia SR Linux",
  devices: [
    {
      id: "srl1",
      label: "SR Linux Router 1",
      role: "router",
      os: "Nokia SR Linux",
      cli_profile: "sr_cli"
    },
    {
      id: "client1",
      label: "Client 1",
      role: "client",
      os: "Linux",
      cli_profile: "linux_shell"
    }
  ],
  addressing_table: [
    {
      device: "srl1",
      interface: "ethernet-1/1",
      ip_address: "10.10.10.1/24",
      role: "default gateway for client1",
      connects_to: "client1 eth1"
    },
    {
      device: "client1",
      interface: "eth1",
      ip_address: "10.10.10.10/24",
      default_gateway: "10.10.10.1",
      connects_to: "srl1 ethernet-1/1"
    }
  ],
  student_tasks: [
    "Inspect the topology and identify the router and client roles.",
    "Compare the live device state with the addressing table.",
    "Verify the client default gateway.",
    "Restore the expected connectivity and run validation."
  ]
};

const DIFFICULTY_PREVIEWS = {
  easy: {
    title: "Guided gateway repair",
    topology: "SR Linux router + Linux client",
    summary: "A focused starter challenge for addressing, default gateway, and direct connectivity.",
    topics: ["Default gateway", "IP addressing", "ICMP connectivity"]
  },
  medium: {
    title: "Intermediate live troubleshooting",
    topology: "SR Linux router + Linux client",
    summary: "A broader SR Linux practice mode with live validation and careful state comparison.",
    topics: ["Addressing table", "Routing requirements", "Connectivity validation"]
  },
  hard: {
    title: "Advanced SR Linux practice",
    topology: "SR Linux router + Linux client",
    summary: "A higher challenge level for validating the same professional network realism scenario under stricter expectations.",
    topics: ["Live device state", "Gateway repair", "End-to-end reasoning"]
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

function getPreferredScenario(scenarios) {
  return (
    scenarios.find((scenario) => scenario.id === CAMPUS_SCENARIO_ID) ||
    scenarios.find((scenario) => scenario.id === DEFAULT_SCENARIO_ID) ||
    scenarios[0] ||
    FALLBACK_SRL_SCENARIO
  );
}

function getScenarioList(scenarios) {
  return scenarios.length > 0 ? scenarios : [FALLBACK_SRL_SCENARIO];
}

function getDefaultScenarioId(scenarios) {
  return getPreferredScenario(scenarios)?.id || DEFAULT_SCENARIO_ID;
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

  return 1;
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

  return "SR Linux CLI + Linux Shell";
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
  const [selectedScenarioId, setSelectedScenarioId] = useState(DEFAULT_SCENARIO_ID);
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
        const normalizedScenarios = normalizeScenarios(data?.scenarios);

        if (isMounted) {
          setScenarios(normalizedScenarios);

          setSelectedScenarioId((currentScenarioId) => {
            const currentScenarioExists = normalizedScenarios.some(
              (scenario) => scenario.id === currentScenarioId
            );

            return currentScenarioExists
              ? currentScenarioId
              : getDefaultScenarioId(normalizedScenarios);
          });

          if (normalizedScenarios.length === 0) {
            setScenarioLoadMessage(
              "Scenario catalog returned no visible scenarios. The default SR Linux scenario will still be used."
            );
          }
        }
      } catch (error) {
        console.error("Scenario catalog could not be loaded.", error);

        if (isMounted) {
          setScenarios([]);
          setSelectedScenarioId(DEFAULT_SCENARIO_ID);
          setScenarioLoadMessage(
            "Scenario catalog could not be loaded. The default SR Linux scenario will still be used."
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

  const availableScenarios = useMemo(() => {
    return getScenarioList(scenarios);
  }, [scenarios]);

  const selectedScenario = useMemo(() => {
    return (
      availableScenarios.find((scenario) => scenario.id === selectedScenarioId) ||
      getPreferredScenario(availableScenarios)
    );
  }, [availableScenarios, selectedScenarioId]);

  async function handleCreateLab() {
    setIsCreating(true);
    setErrorMessage("");
    setErrorDetails("");
    setActiveLabConflict(null);

    try {
      const newLab = await createLab({
        student_id: signedInStudentId,
        difficulty,
        scenario_id: selectedScenario?.id || DEFAULT_SCENARIO_ID
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
              Select a network realism scenario and difficulty level.
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
              <h3>Scenario</h3>
              <p className="muted">
                Choose a professional network realism scenario from the backend catalog.
              </p>
            </div>
          </div>

          {scenarioLoadMessage && (
            <MessageBox
              type="info"
              title="Scenario catalog fallback"
              message={scenarioLoadMessage}
            />
          )}

          <div className="scenario-card-grid scenario-card-grid-selectable">
            {availableScenarios.map((scenario) => {
              const isSelected = selectedScenario?.id === scenario.id;

              return (
                <button
                  className={`lab-type-card scenario-select-card ${isSelected ? "selected" : ""}`}
                  key={scenario.id}
                  type="button"
                  aria-pressed={isSelected}
                  onClick={() => setSelectedScenarioId(scenario.id)}
                >
                  <span className="badge neutral">
                    {scenario.id === CAMPUS_SCENARIO_ID
                      ? "Campus Scenario"
                      : isLoadingScenarios
                        ? "Loading Scenario"
                        : "Network Realism Scenario"}
                  </span>

                  <strong>{scenario.title || FALLBACK_SRL_SCENARIO.title}</strong>
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

        <div className="lab-choice-section">
          <div className="section-title-row compact">
            <div>
              <h3>Choose Difficulty</h3>
              <p className="muted">
                Difficulty controls the expected challenge level and validation behavior.
              </p>
            </div>
          </div>

          <div className="difficulty-card-grid" role="radiogroup" aria-label="Lab difficulty">
            {difficulties.map((item) => {
              const preview = DIFFICULTY_PREVIEWS[item.value] || {
                title: item.label || formatDifficulty(item.value, t),
                topology: "SR Linux router + Linux client",
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

        <h3>{selectedScenario?.title || FALLBACK_SRL_SCENARIO.title}</h3>
        <p className="muted">{getScenarioDisplaySummary(selectedScenario)}</p>

        <div className="info-row">
          <span>Lab Type</span>
          <strong>SR Linux Network Realism</strong>
        </div>

        <div className="info-row">
          <span>Router OS</span>
          <strong>{selectedScenario?.router_os || "Nokia SR Linux"}</strong>
        </div>

        <div className="info-row">
          <span>Topology</span>
          <strong>
            {getScenarioDeviceCount(selectedScenario)} devices / {getScenarioLinkCount(selectedScenario)} {getScenarioLinkCount(selectedScenario) === 1 ? "link" : "links"}
          </strong>
        </div>

        <div className="info-row">
          <span>Workspace</span>
          <strong>Web CLI + topology view</strong>
        </div>

        <div className="info-row">
          <span>Validation</span>
          <strong>{selectedScenario?.runtime_profile === "deploy_only" ? "Deploy-only foundation" : "Live SR Linux validation"}</strong>
        </div>

        <h4>Scenario tasks</h4>
        <ul className="list">
          {(selectedScenario?.student_tasks || FALLBACK_SRL_SCENARIO.student_tasks).map((task) => (
            <li key={task}>{task}</li>
          ))}
        </ul>

        <h4>Difficulty focus</h4>
        <ul className="list">
          {(selectedPreview.topics || []).map((topic) => (
            <li key={topic}>{topic}</li>
          ))}
        </ul>

        {selectedDifficulty?.description && (
          <p className="footer-note">{selectedDifficulty.description}</p>
        )}
      </section>
    </div>
  );
}

export default CreateLab;
