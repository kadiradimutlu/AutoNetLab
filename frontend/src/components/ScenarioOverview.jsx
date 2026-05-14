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

function getScenarioSource(labSession) {
  return (
    labSession?.scenario_overview ||
    labSession?.scenario ||
    labSession?.scenario_metadata ||
    labSession?.metadata ||
    {}
  );
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

function ScenarioOverview({ labSession, t }) {
  if (!labSession) {
    return null;
  }

  const difficultyClass = getDifficultyClass(labSession.difficulty);
  const topics = getTopics(labSession);
  const hints = getHints(labSession);

  return (
    <section className="scenario-overview">
      <MessageBox
        type="info"
        title="Student View"
        message="This screen intentionally hides injected error details. Use the topology, CLI access, and general hints to troubleshoot the lab."
      />

      <div className="section-title-row">
        <div>
          <h4>Scenario Overview</h4>
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
          <span className="muted">Student-safe Mode</span>
          <strong>Enabled</strong>
        </div>
      </div>

      <div className="topic-pill-list">
        {topics.map((topic, index) => (
          <span className="topic-pill" key={`${topic}-${index}`}>
            {String(topic).replace(/_/g, " ")}
          </span>
        ))}
      </div>

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
