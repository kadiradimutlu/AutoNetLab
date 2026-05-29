import MessageBox from "./MessageBox";
import {
  formatDifficulty,
  formatStatus,
  getDifficultyClass
} from "../utils/formatters";

const DEFAULT_TOPIC_LABELS = {
  easy: ["IP Addressing", "Interface Status"],
  medium: ["IP Addressing", "Routing", "Connectivity"],
  hard: ["IP Addressing", "Routing", "Interface Status", "ACL", "Multi-step Troubleshooting"]
};

const DEFAULT_STUDENT_HINTS = [
  "Check IP addressing and subnet masks.",
  "Verify interface status before testing connectivity.",
  "Review routing and default gateway configuration.",
  "Compare addressing, interfaces, and routing step by step across the topology."
];

function normalizeList(value) {
  if (!value) {
    return [];
  }

  if (Array.isArray(value)) {
    return value.filter(Boolean);
  }

  return [value];
}

function hasRichScenarioFields(scenario) {
  return Boolean(
    scenario?.objective ||
      scenario?.story ||
      scenario?.devices ||
      scenario?.addressing_table ||
      scenario?.routing_requirements ||
      scenario?.expected_connectivity ||
      scenario?.student_tasks ||
      scenario?.student_notes
  );
}

function getScenarioSource(labSession) {
  const scenario = labSession?.scenario || labSession?.scenario_metadata || {};
  const overview = labSession?.scenario_overview || {};

  if (hasRichScenarioFields(scenario)) {
    return scenario;
  }

  return overview || scenario || labSession?.metadata || {};
}

function getTopics(labSession) {
  const scenario = getScenarioSource(labSession);
  const explicitTopics = normalizeList(
    scenario.topics ||
      scenario.topic_focus ||
      scenario.focus_topics ||
      labSession?.topics ||
      labSession?.topic_focus
  );

  if (explicitTopics.length > 0) {
    return explicitTopics;
  }

  return DEFAULT_TOPIC_LABELS[String(labSession?.difficulty || "easy").toLowerCase()] || DEFAULT_TOPIC_LABELS.easy;
}

function getHints(labSession) {
  const scenario = getScenarioSource(labSession);
  const hints = normalizeList(scenario.hints || labSession?.hints);

  return hints.length > 0 ? hints : DEFAULT_STUDENT_HINTS;
}

function getScenarioTitle(labSession) {
  const scenario = getScenarioSource(labSession);

  return scenario.title || scenario.name || "Scenario Overview";
}

function getScenarioDescription(labSession) {
  const scenario = getScenarioSource(labSession);

  if (scenario.summary || scenario.description) {
    return scenario.summary || scenario.description;
  }

  const difficulty = String(labSession?.difficulty || "easy").toLowerCase();

  if (difficulty === "hard") {
    return "This hard scenario combines multiple troubleshooting topics. Work through the topology carefully and validate only after checking each device.";
  }

  if (difficulty === "medium") {
    return "This medium scenario includes more than one issue area. Use the topology, CLI access, and general hints to narrow down the problem.";
  }

  return "This scenario focuses on basic troubleshooting steps and safe validation feedback.";
}

function getSafeText(value, fallback = "-") {
  if (value === undefined || value === null || value === "") {
    return fallback;
  }

  return String(value);
}

function getDeviceLabel(device) {
  return device?.label || device?.id || device?.name || "Device";
}

function ScenarioDataTable({ columns, rows, emptyMessage }) {
  if (!rows.length) {
    return (
      <div className="scenario-empty-state">
        <p>{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className="scenario-table-scroll">
      <table className="scenario-data-table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key}>{column.label}</th>
            ))}
          </tr>
        </thead>

        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={`${row.device || row.source || "row"}-${rowIndex}`}>
              {columns.map((column) => (
                <td key={column.key}>{getSafeText(row[column.key])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ScenarioOverview({ labSession, t }) {
  if (!labSession) {
    return null;
  }

  const scenario = getScenarioSource(labSession);
  const difficultyClass = getDifficultyClass(labSession.difficulty);
  const topics = getTopics(labSession);
  const hints = getHints(labSession);
  const devices = normalizeList(scenario.devices);
  const addressingTable = normalizeList(scenario.addressing_table);
  const routingRequirements = normalizeList(scenario.routing_requirements);
  const expectedConnectivity = normalizeList(scenario.expected_connectivity);
  const studentTasks = normalizeList(scenario.student_tasks);
  const studentNotes = normalizeList(scenario.student_notes);
  const hasScenarioDesign =
    hasRichScenarioFields(scenario) ||
    devices.length > 0 ||
    addressingTable.length > 0 ||
    routingRequirements.length > 0 ||
    expectedConnectivity.length > 0 ||
    studentTasks.length > 0 ||
    studentNotes.length > 0;

  return (
    <section className="scenario-overview">
      <MessageBox
        type="info"
        title="Student View"
        message="Injected faults are intentionally hidden. Use the design requirements, topology, CLI access, and validation feedback as the expected state."
      />

      <div className="section-title-row">
        <div>
          <h4>{getScenarioTitle(labSession)}</h4>
          <p className="muted">{getScenarioDescription(labSession)}</p>
        </div>

        <span className={`badge ${difficultyClass}`}>
          {formatDifficulty(labSession.difficulty, t)}
        </span>
      </div>

      <div className="scenario-meta-grid">
        <div>
          <span className="muted">Session Status</span>
          <strong>{formatStatus(labSession.status, t)}</strong>
        </div>

        <div>
          <span className="muted">Visible Topics</span>
          <strong>{topics.length}</strong>
        </div>

        <div>
          <span className="muted">Learning Mode</span>
          <strong>Enabled</strong>
        </div>
      </div>

      {topics.length > 0 && (
        <div className="topic-pill-list">
          {topics.map((topic, index) => (
            <span className="topic-pill" key={`${topic}-${index}`}>
              {String(topic).replace(/_/g, " ")}
            </span>
          ))}
        </div>
      )}

      {hasScenarioDesign && (
        <div className="scenario-detail-grid">
          {scenario.objective && (
            <div className="scenario-detail-card scenario-detail-card-wide">
              <h4>Objective</h4>
              <p>{scenario.objective}</p>
            </div>
          )}

          {scenario.story && (
            <div className="scenario-detail-card scenario-detail-card-wide">
              <h4>Design Requirements</h4>
              <p>{scenario.story}</p>
            </div>
          )}

          {devices.length > 0 && (
            <div className="scenario-detail-card scenario-detail-card-wide">
              <div className="section-title-row compact">
                <div>
                  <h4>Devices</h4>
                  <p className="muted">Student-safe device roles and operating systems.</p>
                </div>
              </div>

              <div className="scenario-device-grid">
                {devices.map((device, index) => (
                  <article className="scenario-device-card" key={`${device?.id || "device"}-${index}`}>
                    <strong>{getDeviceLabel(device)}</strong>
                    <div className="scenario-device-meta">
                      <span>{getSafeText(device?.role, "device")}</span>
                      <span>{getSafeText(device?.os || device?.kind, "Network OS")}</span>
                    </div>
                    <p>{getSafeText(device?.image, "Image metadata unavailable")}</p>
                  </article>
                ))}
              </div>
            </div>
          )}

          {addressingTable.length > 0 && (
            <div className="scenario-detail-card scenario-detail-card-wide">
              <h4>Addressing Table</h4>
              <ScenarioDataTable
                columns={[
                  { key: "device", label: "Device" },
                  { key: "interface", label: "Interface" },
                  { key: "ip_address", label: "IP Address" },
                  { key: "default_gateway", label: "Default Gateway" },
                  { key: "role", label: "Role" },
                  { key: "connects_to", label: "Connects To" }
                ]}
                rows={addressingTable}
                emptyMessage="No addressing requirements are available."
              />
            </div>
          )}

          {routingRequirements.length > 0 && (
            <div className="scenario-detail-card">
              <h4>Routing Requirements</h4>
              <ul className="scenario-requirement-list">
                {routingRequirements.map((item, index) => (
                  <li key={`${item?.device || "requirement"}-${index}`}>
                    <strong>{getSafeText(item?.device, "Device")}</strong>
                    <span>{getSafeText(item?.requirement || item?.description || item)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {expectedConnectivity.length > 0 && (
            <div className="scenario-detail-card">
              <h4>Expected Connectivity</h4>
              <ScenarioDataTable
                columns={[
                  { key: "source", label: "Source" },
                  { key: "destination", label: "Destination" },
                  { key: "protocol", label: "Protocol" },
                  { key: "expectation", label: "Expectation" }
                ]}
                rows={expectedConnectivity}
                emptyMessage="No expected connectivity checks are available."
              />
            </div>
          )}

          {studentTasks.length > 0 && (
            <div className="scenario-detail-card">
              <h4>Student Tasks</h4>
              <ol className="scenario-task-list">
                {studentTasks.map((task, index) => (
                  <li key={`${task}-${index}`}>{task}</li>
                ))}
              </ol>
            </div>
          )}

          {studentNotes.length > 0 && (
            <div className="scenario-detail-card">
              <h4>Student Notes</h4>
              <ul className="scenario-note-list">
                {studentNotes.map((note, index) => (
                  <li key={`${note}-${index}`}>{note}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      <h4>General Hints</h4>
      <div className="hints-list">
        {hints.map((hint, index) => (
          <div className="hint-item" key={`${hint}-${index}`}>
            <span className="hint-number">{index + 1}</span>
            <p>{hint}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

export default ScenarioOverview;

