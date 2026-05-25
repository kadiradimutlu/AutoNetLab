import { useEffect, useMemo, useState } from "react";
import AnalyticsEmptyState from "../components/AnalyticsEmptyState";
import AnalyticsSummaryCards from "../components/AnalyticsSummaryCards";
import DifficultyDistributionChart from "../components/DifficultyDistributionChart";
import RecentSessionsTable from "../components/RecentSessionsTable";
import TopicWeaknessList from "../components/TopicWeaknessList";
import MessageBox from "../components/MessageBox";
import RuntimeReadinessCard from "../components/RuntimeReadinessCard";
import DatabaseReadinessCard from "../components/DatabaseReadinessCard";
import {
  getDifficultyDistribution,
  finishLab,
  getErrorDetails,
  getErrorMessage,
  getInstructorSummary,
  getInstructorStudentScoreTrend,
  getInstructorStudentSessions,
  getInstructorStudentSummary,
  getInstructorStudents,
  getInstructorStudentTopicWeaknesses,
  getRecentSessions,
  getRuntimeReadiness,
  getDatabaseReadiness,
  getTopicWeaknesses
} from "../services/apiService";

function formatNumber(value, fallback = "0") {
  if (value === undefined || value === null || value === "") {
    return fallback;
  }

  const numericValue = Number(value);

  if (Number.isNaN(numericValue)) {
    return String(value);
  }

  return numericValue.toLocaleString("en-US", {
    maximumFractionDigits: 2
  });
}

function formatPercent(value) {
  if (value === undefined || value === null || value === "") {
    return "-";
  }

  const numericValue = Number(value);

  if (Number.isNaN(numericValue)) {
    return "-";
  }

  return `${numericValue.toFixed(1)}%`;
}

function formatDateTime(value) {
  if (!value) {
    return "-";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return date.toLocaleString("en-US", {
    dateStyle: "medium",
    timeStyle: "short"
  });
}

function formatTitleCase(value) {
  const normalizedValue = String(value || "").replace(/_/g, " ").trim();

  if (!normalizedValue) {
    return "-";
  }

  return normalizedValue
    .split(" ")
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

function getLifecycleStatusLabel(status) {
  const normalizedStatus = String(status || "").toLowerCase();

  const statusLabels = {
    created: "Created",
    deployed: "Deployed",
    active: "Active",
    validated: "Validated",
    finished: "Finished",
    destroyed: "Destroyed",
    error: "Error"
  };

  return statusLabels[normalizedStatus] || formatTitleCase(status);
}

function getLifecycleStatusBadgeClass(status) {
  const normalizedStatus = String(status || "").toLowerCase();

  if (normalizedStatus === "error") {
    return "fail";
  }

  if (["created", "deployed", "active", "validated"].includes(normalizedStatus)) {
    return "medium";
  }

  if (["finished", "destroyed"].includes(normalizedStatus)) {
    return "neutral";
  }

  return "neutral";
}

function getValidationResultLabel(passed) {
  if (passed === true) {
    return "PASS";
  }

  if (passed === false) {
    return "FAIL";
  }

  return "Not Validated";
}

function getValidationResultBadgeClass(passed) {
  if (passed === true) {
    return "pass";
  }

  if (passed === false) {
    return "fail";
  }

  return "neutral";
}

function getSessionLastActivityAt(session) {
  return session?.completed_at || session?.updated_at || session?.created_at;
}

function isForceClosableLabStatus(status) {
  return ["created", "deployed", "active", "validated"].includes(
    String(status || "").toLowerCase()
  );
}

function getForceClosableSessions(sessions) {
  return Array.isArray(sessions)
    ? sessions.filter((session) => isForceClosableLabStatus(session.status))
    : [];
}

function getSeverityClass(severity) {
  const normalizedSeverity = String(severity || "").toLowerCase();

  if (normalizedSeverity.includes("high")) {
    return "fail";
  }

  if (normalizedSeverity.includes("low")) {
    return "pass";
  }

  return "medium";
}

function normalizeStudentId(student) {
  return student?.student_id || student?.username || student?.id || "";
}

const INSTRUCTOR_PORTAL_TABS = [
  {
    id: "home",
    label: "Home"
  },
  {
    id: "students",
    label: "Students"
  },
  {
    id: "analytics",
    label: "Analytics"
  },
  {
    id: "system",
    label: "System Readiness"
  }
];

const STUDENT_DETAIL_TABS = [
  {
    id: "overview",
    label: "Overview"
  },
  {
    id: "weaknesses",
    label: "Weaknesses"
  },
  {
    id: "scoreTrend",
    label: "Score Trend"
  },
  {
    id: "sessions",
    label: "Sessions"
  }
];

const ANALYTICS_DETAIL_TABS = [
  {
    id: "difficulty",
    label: "Difficulty Distribution"
  },
  {
    id: "weaknesses",
    label: "Topic Weakness Analytics"
  },
  {
    id: "recentSessions",
    label: "Recent Sessions"
  }
];

function getReadinessStatusLabel(readiness, isLoading, errorMessage) {
  if (isLoading) {
    return "Checking";
  }

  if (errorMessage) {
    return "Unavailable";
  }

  if (readiness?.ready === true) {
    return "Ready";
  }

  if (readiness?.ready === false) {
    return "Needs Attention";
  }

  return "Not Checked";
}

function getReadinessBadgeClass(readiness, isLoading, errorMessage) {
  if (isLoading) {
    return "neutral";
  }

  if (errorMessage || readiness?.ready === false) {
    return "fail";
  }

  if (readiness?.ready === true) {
    return "pass";
  }

  return "neutral";
}

function getSystemStatus({
  runtimeReadiness,
  databaseReadiness,
  isRuntimeReadinessLoading,
  isDatabaseReadinessLoading,
  runtimeReadinessError,
  databaseReadinessError
}) {
  if (isRuntimeReadinessLoading || isDatabaseReadinessLoading) {
    return {
      label: "Checking",
      badgeClass: "neutral",
      helper: "System checks are refreshing."
    };
  }

  if (runtimeReadinessError || databaseReadinessError) {
    return {
      label: "Needs Attention",
      badgeClass: "fail",
      helper: "One or more system checks could not be completed."
    };
  }

  if (runtimeReadiness?.ready === true && databaseReadiness?.ready === true) {
    return {
      label: "Ready",
      badgeClass: "pass",
      helper: "Lab runtime and persistence checks are healthy."
    };
  }

  if (!runtimeReadiness && !databaseReadiness) {
    return {
      label: "Not Checked",
      badgeClass: "neutral",
      helper: "Refresh system status to verify runtime and persistence."
    };
  }

  return {
    label: "Needs Attention",
    badgeClass: "medium",
    helper: "Review the readiness cards for details."
  };
}

function InstructorPortalTabs({ activeTab, onChange }) {
  return (
    <div className="instructor-portal-tabs" role="tablist" aria-label="Instructor Portal sections">
      {INSTRUCTOR_PORTAL_TABS.map((tab) => (
        <button
          aria-selected={activeTab === tab.id}
          className={`instructor-portal-tab ${activeTab === tab.id ? "active" : ""}`}
          key={tab.id}
          onClick={() => onChange(tab.id)}
          role="tab"
          type="button"
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

function StudentDetailTabs({ activeTab, onChange }) {
  return (
    <div className="instructor-portal-tabs student-detail-tabs" role="tablist" aria-label="Selected student detail sections">
      {STUDENT_DETAIL_TABS.map((tab) => (
        <button
          aria-selected={activeTab === tab.id}
          className={`instructor-portal-tab ${activeTab === tab.id ? "active" : ""}`}
          key={tab.id}
          onClick={() => onChange(tab.id)}
          role="tab"
          type="button"
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

function AnalyticsDetailTabs({ activeTab, onChange }) {
  return (
    <div className="instructor-portal-tabs analytics-detail-tabs" role="tablist" aria-label="Instructor analytics sections">
      {ANALYTICS_DETAIL_TABS.map((tab) => (
        <button
          aria-selected={activeTab === tab.id}
          className={`instructor-portal-tab ${activeTab === tab.id ? "active" : ""}`}
          key={tab.id}
          onClick={() => onChange(tab.id)}
          role="tab"
          type="button"
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

function PortalOverviewCards({
  summary,
  students,
  systemStatus
}) {
  const cards = [
    {
      title: "Total Sessions",
      value: formatNumber(summary?.total_sessions, "-"),
      helper: "All tracked lab sessions"
    },
    {
      title: "Completed Sessions",
      value: formatNumber(summary?.completed_sessions, "-"),
      helper: "Validated or finished sessions"
    },
    {
      title: "Average Score",
      value: formatNumber(summary?.average_score, "-"),
      helper: "Score range: 0-100"
    },
    {
      title: "Pass Rate",
      value: formatPercent(summary?.pass_rate),
      helper: "Passed sessions / completed sessions"
    },
    {
      title: "Active Students",
      value: formatNumber(students.length, "0"),
      helper: "Students visible to instructor"
    },
    {
      title: "System Status",
      value: systemStatus.label,
      helper: systemStatus.helper,
      statusClass: systemStatus.badgeClass
    }
  ];

  return (
    <section className="portal-overview-grid">
      {cards.map((card) => (
        <div
          className={`portal-overview-card ${card.statusClass ? `status-${card.statusClass}` : ""}`}
          key={card.title}
        >
          <span>{card.title}</span>
          <strong>{card.value}</strong>
          <p>{card.helper}</p>
        </div>
      ))}
    </section>
  );
}

function SystemReadinessSummary({
  runtimeReadiness,
  databaseReadiness,
  isRuntimeReadinessLoading,
  isDatabaseReadinessLoading,
  runtimeReadinessError,
  databaseReadinessError,
  systemStatus
}) {
  return (
    <section className="card instructor-system-summary-card">
      <div className="section-title-row">
        <div>
          <h3>System Readiness</h3>
          <p className="muted">
            High-level operational status for lab runtime, CLI access, and persistence.
          </p>
        </div>

        <span className={`badge ${systemStatus.badgeClass}`}>
          {systemStatus.label}
        </span>
      </div>

      <div className="instructor-system-summary-grid">
        <div>
          <span>Runtime</span>
          <strong>
            {getReadinessStatusLabel(
              runtimeReadiness,
              isRuntimeReadinessLoading,
              runtimeReadinessError
            )}
          </strong>
          <span className={`badge ${getReadinessBadgeClass(runtimeReadiness, isRuntimeReadinessLoading, runtimeReadinessError)}`}>
            Docker + Containerlab
          </span>
        </div>

        <div>
          <span>Database</span>
          <strong>
            {getReadinessStatusLabel(
              databaseReadiness,
              isDatabaseReadinessLoading,
              databaseReadinessError
            )}
          </strong>
          <span className={`badge ${getReadinessBadgeClass(databaseReadiness, isDatabaseReadinessLoading, databaseReadinessError)}`}>
            PostgreSQL
          </span>
        </div>

        <div>
          <span>CLI Mode</span>
          <strong>{runtimeReadiness?.current_mode || "-"}</strong>
          <p className="muted">Used by student workspace sessions.</p>
        </div>
      </div>
    </section>
  );
}

function StudentListPanel({
  students,
  selectedStudentId,
  onSelectStudent,
  isLoading
}) {
  return (
    <section className="card instructor-student-list-card">
      <div className="section-title-row">
        <div>
          <h3>Students</h3>
          <p className="muted">
            Select a student to inspect lab history and performance details.
          </p>
        </div>

        <span className="badge neutral">{students.length} students</span>
      </div>

      {isLoading && <p className="muted">Loading students...</p>}

      {!isLoading && students.length === 0 && (
        <AnalyticsEmptyState
          title="No students found."
          message="Student analytics will appear after lab sessions are created."
        />
      )}

      <div className="student-list">
        {students.map((student) => {
          const studentId = normalizeStudentId(student);
          const isSelected = selectedStudentId === studentId;

          return (
            <button
              className={`student-list-item ${isSelected ? "active" : ""}`}
              key={studentId}
              onClick={() => onSelectStudent(studentId)}
              type="button"
            >
              <div>
                <strong>{studentId}</strong>
                <span className="muted">
                  Last activity: {formatDateTime(student.last_activity_at)}
                </span>
              </div>

              <div className="student-list-metrics">
                <span>{formatNumber(student.completed_sessions)} completed</span>
                <span>{formatPercent(student.pass_rate)} pass rate</span>
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
}

function StudentSummaryCards({ summary, compact = false }) {
  const cards = [
    {
      title: "Total Sessions",
      value: formatNumber(summary?.total_sessions)
    },
    {
      title: "Completed",
      value: formatNumber(summary?.completed_sessions)
    },
    {
      title: "Active",
      value: formatNumber(summary?.active_sessions)
    },
    {
      title: "Average Score",
      value: summary?.average_score === null || summary?.average_score === undefined
        ? "-"
        : formatNumber(summary.average_score)
    },
    {
      title: "Pass Rate",
      value: formatPercent(summary?.pass_rate)
    }
  ];

  return (
    <div className={`student-summary-grid ${compact ? "compact" : ""}`}>
      {cards.map((card) => (
        <div className="metric-card" key={card.title}>
          <span>{card.title}</span>
          <strong>{card.value}</strong>
        </div>
      ))}
    </div>
  );
}

function StudentDetailOverview({
  sessions,
  topicWeaknesses,
  closingSessionId,
  onForceCloseLab
}) {
  const activeSessions = getForceClosableSessions(sessions);
  const priorityWeaknesses = Array.isArray(topicWeaknesses)
    ? topicWeaknesses.slice(0, 3)
    : [];

  return (
    <section className="card">
      <div className="section-title-row">
        <div>
          <h3>Student Overview</h3>
          <p className="muted">
            Focused summary for active labs and the highest-priority practice areas.
          </p>
        </div>

        <span className={`badge ${activeSessions.length > 0 ? "medium" : "neutral"}`}>
          {activeSessions.length > 0 ? `${activeSessions.length} active lab${activeSessions.length === 1 ? "" : "s"}` : "No active labs"}
        </span>
      </div>

      <div className="portal-workflow-list">
        <div>
          <strong>Active Labs</strong>

          {activeSessions.length === 0 ? (
            <p>No active lab is currently open for this student.</p>
          ) : (
            activeSessions.map((session) => (
              <div className="result-title-row" key={session.session_id}>
                <div>
                  <strong>{session.session_id}</strong>
                  <p className="muted">
                    {formatTitleCase(session.difficulty)} difficulty - {getLifecycleStatusLabel(session.status)} - Last activity: {formatDateTime(getSessionLastActivityAt(session))}
                  </p>
                </div>

                <button
                  className="secondary-button"
                  disabled={closingSessionId === session.session_id}
                  onClick={() => onForceCloseLab(session)}
                  type="button"
                >
                  {closingSessionId === session.session_id ? "Closing..." : "Force Close Lab"}
                </button>
              </div>
            ))
          )}
        </div>

        <div>
          <strong>Priority Weaknesses</strong>

          {priorityWeaknesses.length === 0 ? (
            <p>No topic weakness data is available for this student yet.</p>
          ) : (
            priorityWeaknesses.map((topic) => (
              <p key={topic.topic || topic.label}>
                {topic.label || topic.topic || "Unknown topic"} - Failure Rate: {formatPercent(topic.failure_rate)} - Average Score: {formatNumber(topic.average_score, "-")}
              </p>
            ))
          )}
        </div>
      </div>
    </section>
  );
}

function StudentSessionsTable({ sessions }) {
  return (
    <section className="card">
      <div className="section-title-row">
        <div>
          <h3>Session History</h3>
          <p className="muted">
            Recent lab sessions completed or started by the selected student.
          </p>
        </div>

        <span className="badge neutral">{sessions.length} sessions</span>
      </div>

      {sessions.length === 0 ? (
        <AnalyticsEmptyState
          title="No sessions found."
          message="This student does not have lab session history yet."
        />
      ) : (
        <div className="table-wrapper">
          <table className="analytics-table">
            <thead>
              <tr>
                <th>Session ID</th>
                <th>Difficulty</th>
                <th>Status</th>
                <th>Score</th>
                <th>Result</th>
                <th>Created</th>
                <th>Last Activity</th>
              </tr>
            </thead>

            <tbody>
              {sessions.map((session) => (
                <tr key={session.session_id}>
                  <td>{session.session_id}</td>
                  <td>
                    <span className={`badge ${String(session.difficulty || "").toLowerCase()}`}>
                      {session.difficulty || "-"}
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${getLifecycleStatusBadgeClass(session.status)}`}>
                      {getLifecycleStatusLabel(session.status)}
                    </span>
                  </td>
                  <td>{session.score === null || session.score === undefined ? "-" : formatNumber(session.score)}</td>
                  <td>
                    <span className={`badge ${getValidationResultBadgeClass(session.passed)}`}>
                      {getValidationResultLabel(session.passed)}
                    </span>
                  </td>
                  <td>{formatDateTime(session.created_at)}</td>
                  <td>{formatDateTime(getSessionLastActivityAt(session))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function StudentTopicWeaknesses({ topicWeaknesses }) {
  return (
    <section className="card">
      <div className="section-title-row">
        <div>
          <h3>Topic Weaknesses</h3>
          <p className="muted">
            Topics where the selected student needs more practice.
          </p>
        </div>

        <span className="badge neutral">{topicWeaknesses.length} topics</span>
      </div>

      {topicWeaknesses.length === 0 ? (
        <AnalyticsEmptyState
          title="No topic weaknesses found."
          message="Weakness analytics will appear after validation attempts."
        />
      ) : (
        <div className="topic-weakness-grid">
          {topicWeaknesses.map((topic) => (
            <div className="topic-weakness-card" key={topic.topic || topic.label}>
              <div className="result-title-row">
                <strong>{topic.label || topic.topic || "Unknown topic"}</strong>
                <span className={`badge ${getSeverityClass(topic.severity)}`}>
                  {topic.severity || "medium"}
                </span>
              </div>

              <div className="topic-weakness-metrics">
                <div>
                  <span>Failures</span>
                  <strong>{formatNumber(topic.fail_count)}</strong>
                </div>

                <div>
                  <span>Attempts</span>
                  <strong>{formatNumber(topic.attempt_count)}</strong>
                </div>

                <div>
                  <span>Failure Rate</span>
                  <strong>{formatPercent(topic.failure_rate)}</strong>
                </div>

                <div>
                  <span>Average Score</span>
                  <strong>{formatNumber(topic.average_score, "-")}</strong>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function StudentScoreTrend({ scoreTrend }) {
  const validScores = scoreTrend
    .map((item) => Number(item.score))
    .filter((score) => !Number.isNaN(score));

  const maxScore = Math.max(...validScores, 100);

  return (
    <section className="card">
      <div className="section-title-row">
        <div>
          <h3>Score Trend</h3>
          <p className="muted">
            Chronological score development for recent student sessions.
          </p>
        </div>

        <span className="badge neutral">{scoreTrend.length} points</span>
      </div>

      {scoreTrend.length === 0 ? (
        <AnalyticsEmptyState
          title="No score trend found."
          message="Score trend data will appear after the student completes validations."
        />
      ) : (
        <>
          <div className="score-trend-chart">
            {scoreTrend.map((item, index) => {
              const score = Number(item.score);
              const safeScore = Number.isNaN(score) ? 0 : Math.max(score, 0);
              const heightPercent = maxScore ? Math.max((safeScore / maxScore) * 100, 4) : 4;

              return (
                <div className="score-trend-bar-item" key={`${item.session_id}-${index}`}>
                  <div className="score-trend-bar-track">
                    <div
                      className={`score-trend-bar ${item.passed ? "pass" : "fail"}`}
                      style={{ height: `${heightPercent}%` }}
                      title={`${item.session_id}: ${Number.isNaN(score) ? "No score" : score}`}
                    />
                  </div>

                  <span>{Number.isNaN(score) ? "-" : Math.round(score)}</span>
                </div>
              );
            })}
          </div>

          <div className="table-wrapper compact">
            <table className="analytics-table">
              <thead>
                <tr>
                  <th>Session ID</th>
                  <th>Difficulty</th>
                  <th>Status</th>
                  <th>Score</th>
                  <th>Created</th>
                </tr>
              </thead>

              <tbody>
                {scoreTrend.map((item) => (
                  <tr key={item.session_id}>
                    <td>{item.session_id}</td>
                    <td>{item.difficulty || "-"}</td>
                    <td>
                      <span className={`badge ${getLifecycleStatusBadgeClass(item.status)}`}>
                        {getLifecycleStatusLabel(item.status)}
                      </span>
                    </td>
                    <td>{item.score === null || item.score === undefined ? "-" : formatNumber(item.score)}</td>
                    <td>{formatDateTime(item.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}

function InstructorDashboardPage() {
  const [students, setStudents] = useState([]);
  const [selectedStudentId, setSelectedStudentId] = useState("");
  const [summary, setSummary] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [topicWeaknesses, setTopicWeaknesses] = useState([]);
  const [scoreTrend, setScoreTrend] = useState([]);
  const [isStudentsLoading, setIsStudentsLoading] = useState(true);
  const [isStudentDetailLoading, setIsStudentDetailLoading] = useState(false);
  const [runtimeReadiness, setRuntimeReadiness] = useState(null);
  const [isRuntimeReadinessLoading, setIsRuntimeReadinessLoading] = useState(false);
  const [runtimeReadinessError, setRuntimeReadinessError] = useState("");
  const [runtimeReadinessErrorDetails, setRuntimeReadinessErrorDetails] = useState("");
  const [runtimeReadinessCheckedAt, setRuntimeReadinessCheckedAt] = useState(null);
  const [databaseReadiness, setDatabaseReadiness] = useState(null);
  const [isDatabaseReadinessLoading, setIsDatabaseReadinessLoading] = useState(false);
  const [databaseReadinessError, setDatabaseReadinessError] = useState("");
  const [databaseReadinessErrorDetails, setDatabaseReadinessErrorDetails] = useState("");
  const [databaseReadinessCheckedAt, setDatabaseReadinessCheckedAt] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [errorDetails, setErrorDetails] = useState("");
  const [activeTab, setActiveTab] = useState("home");
  const [globalSummary, setGlobalSummary] = useState(null);
  const [difficultyDistribution, setDifficultyDistribution] = useState([]);
  const [globalTopicWeaknesses, setGlobalTopicWeaknesses] = useState([]);
  const [recentSessions, setRecentSessions] = useState([]);
  const [isGlobalAnalyticsLoading, setIsGlobalAnalyticsLoading] = useState(false);
  const [globalErrorMessage, setGlobalErrorMessage] = useState("");
  const [globalErrorDetails, setGlobalErrorDetails] = useState("");
  const [forceCloseSessionId, setForceCloseSessionId] = useState("");
  const [forceCloseMessage, setForceCloseMessage] = useState("");
  const [forceCloseErrorMessage, setForceCloseErrorMessage] = useState("");
  const [forceCloseErrorDetails, setForceCloseErrorDetails] = useState("");
  const [studentDetailTab, setStudentDetailTab] = useState("overview");
  const [analyticsDetailTab, setAnalyticsDetailTab] = useState("difficulty");


  async function loadGlobalAnalytics() {
    setIsGlobalAnalyticsLoading(true);
    setGlobalErrorMessage("");
    setGlobalErrorDetails("");

    try {
      const [
        summaryResponse,
        difficultyResponse,
        topicWeaknessResponse,
        recentSessionsResponse
      ] = await Promise.all([
        getInstructorSummary(),
        getDifficultyDistribution(),
        getTopicWeaknesses(),
        getRecentSessions(10)
      ]);

      setGlobalSummary(summaryResponse || null);
      setDifficultyDistribution(
        Array.isArray(difficultyResponse?.distribution)
          ? difficultyResponse.distribution
          : []
      );
      setGlobalTopicWeaknesses(
        Array.isArray(topicWeaknessResponse?.topic_weaknesses)
          ? topicWeaknessResponse.topic_weaknesses
          : []
      );
      setRecentSessions(
        Array.isArray(recentSessionsResponse?.recent_sessions)
          ? recentSessionsResponse.recent_sessions
          : []
      );
    } catch (error) {
      setGlobalErrorMessage(
        getErrorMessage(
          error,
          "Instructor analytics could not be loaded."
        )
      );
      setGlobalErrorDetails(getErrorDetails(error));
      console.error("Instructor analytics loading failed.", error);
    } finally {
      setIsGlobalAnalyticsLoading(false);
    }
  }

  async function loadRuntimeReadiness() {
    setIsRuntimeReadinessLoading(true);
    setRuntimeReadinessError("");
    setRuntimeReadinessErrorDetails("");

    try {
      const response = await getRuntimeReadiness();
      setRuntimeReadiness(response || null);
      setRuntimeReadinessCheckedAt(new Date());
    } catch (error) {
      setRuntimeReadinessError(
        getErrorMessage(
          error,
          "Runtime readiness check is unavailable."
        )
      );
      setRuntimeReadinessErrorDetails(getErrorDetails(error));
      setRuntimeReadinessCheckedAt(new Date());
      console.error("Runtime readiness loading failed.", error);
    } finally {
      setIsRuntimeReadinessLoading(false);
    }
  }

  async function loadDatabaseReadiness() {
    setIsDatabaseReadinessLoading(true);
    setDatabaseReadinessError("");
    setDatabaseReadinessErrorDetails("");

    try {
      const response = await getDatabaseReadiness();
      setDatabaseReadiness(response || null);
      setDatabaseReadinessCheckedAt(new Date());
    } catch (error) {
      setDatabaseReadinessError(
        getErrorMessage(
          error,
          "Database readiness check is unavailable."
        )
      );
      setDatabaseReadinessErrorDetails(getErrorDetails(error));
      setDatabaseReadinessCheckedAt(new Date());
      console.error("Database readiness loading failed.", error);
    } finally {
      setIsDatabaseReadinessLoading(false);
    }
  }

  async function loadStudents() {
    setIsStudentsLoading(true);
    setErrorMessage("");
    setErrorDetails("");

    try {
      const response = await getInstructorStudents();
      const studentList = Array.isArray(response?.students) ? response.students : [];

      setStudents(studentList);

      if (studentList.length > 0) {
        const firstStudentId = normalizeStudentId(studentList[0]);
        setSelectedStudentId((currentStudentId) => currentStudentId || firstStudentId);
      } else {
        setSelectedStudentId("");
        setSummary(null);
        setSessions([]);
        setTopicWeaknesses([]);
        setScoreTrend([]);
      }
    } catch (error) {
      setErrorMessage(
        getErrorMessage(
          error,
          "Student analytics could not be loaded."
        )
      );
      setErrorDetails(getErrorDetails(error));
      console.error("Student analytics loading failed.", error);
    } finally {
      setIsStudentsLoading(false);
    }
  }

  async function loadStudentDetails(studentId) {
    if (!studentId) {
      return;
    }

    setIsStudentDetailLoading(true);
    setErrorMessage("");
    setErrorDetails("");

    try {
      const [
        summaryResponse,
        sessionsResponse,
        topicWeaknessResponse,
        scoreTrendResponse
      ] = await Promise.all([
        getInstructorStudentSummary(studentId),
        getInstructorStudentSessions(studentId, 50),
        getInstructorStudentTopicWeaknesses(studentId),
        getInstructorStudentScoreTrend(studentId, 50)
      ]);

      setSummary(summaryResponse || null);
      setSessions(Array.isArray(sessionsResponse?.sessions) ? sessionsResponse.sessions : []);
      setTopicWeaknesses(
        Array.isArray(topicWeaknessResponse?.topic_weaknesses)
          ? topicWeaknessResponse.topic_weaknesses
          : []
      );
      setScoreTrend(
        Array.isArray(scoreTrendResponse?.score_trend)
          ? scoreTrendResponse.score_trend
          : []
      );
    } catch (error) {
      setErrorMessage(
        getErrorMessage(
          error,
          "Selected student analytics could not be loaded."
        )
      );
      setErrorDetails(getErrorDetails(error));
      console.error("Selected student analytics loading failed.", error);
    } finally {
      setIsStudentDetailLoading(false);
    }
  }


  function refreshPortalData() {
    loadGlobalAnalytics();
    loadRuntimeReadiness();
    loadDatabaseReadiness();
    loadStudents();

    if (selectedStudentId) {
      loadStudentDetails(selectedStudentId);
    }
  }

  async function handleForceCloseLab(session) {
    const sessionId = session?.session_id;

    if (!sessionId) {
      return;
    }

    const confirmed = typeof window === "undefined"
      ? true
      : window.confirm(
        `Force close lab ${sessionId}? This will stop the runtime while preserving validation history.`
      );

    if (!confirmed) {
      return;
    }

    setForceCloseSessionId(sessionId);
    setForceCloseMessage("");
    setForceCloseErrorMessage("");
    setForceCloseErrorDetails("");

    try {
      const response = await finishLab(sessionId);

      setForceCloseMessage(
        response?.message ||
          `Lab ${sessionId} was force closed. Validation history is preserved.`
      );

      await Promise.all([
        loadGlobalAnalytics(),
        loadStudents(),
        selectedStudentId ? loadStudentDetails(selectedStudentId) : Promise.resolve()
      ]);
    } catch (error) {
      setForceCloseErrorMessage(
        getErrorMessage(
          error,
          "Lab could not be force closed."
        )
      );
      setForceCloseErrorDetails(getErrorDetails(error));
      console.error("Instructor force close failed.", error);
    } finally {
      setForceCloseSessionId("");
    }
  }

  useEffect(() => {
    loadGlobalAnalytics();
    loadRuntimeReadiness();
    loadDatabaseReadiness();
    loadStudents();
  }, []);


  useEffect(() => {
    setStudentDetailTab("overview");
    loadStudentDetails(selectedStudentId);
  }, [selectedStudentId]);

  const selectedStudent = useMemo(() => {
    return students.find((student) => normalizeStudentId(student) === selectedStudentId);
  }, [students, selectedStudentId]);

  const systemStatus = getSystemStatus({
    runtimeReadiness,
    databaseReadiness,
    isRuntimeReadinessLoading,
    isDatabaseReadinessLoading,
    runtimeReadinessError,
    databaseReadinessError
  });

  return (
    <>
      <section className="hero instructor-portal-hero">
        <div>
          <h2>Instructor Portal</h2>
          <p>
            Monitor student lab progress, performance patterns, topic weaknesses, and system status from one focused workspace.
          </p>
        </div>

        <div className="actions">
          <button
            className="secondary-button"
            onClick={refreshPortalData}
            disabled={
              isStudentsLoading ||
              isStudentDetailLoading ||
              isGlobalAnalyticsLoading ||
              isRuntimeReadinessLoading ||
              isDatabaseReadinessLoading
            }
            type="button"
          >
            {isStudentsLoading || isGlobalAnalyticsLoading ? "Refreshing..." : "Refresh Portal"}
          </button>
        </div>
      </section>

      <InstructorPortalTabs
        activeTab={activeTab}
        onChange={setActiveTab}
      />

      {activeTab === "home" && (
        <div className="instructor-portal-shell">
          <PortalOverviewCards
            summary={globalSummary}
            students={students}
            systemStatus={systemStatus}
          />

          <div className="two-column instructor-home-grid">
            <section className="card instructor-home-card">
              <div className="section-title-row">
                <div>
                  <h3>Instructor Workspace</h3>
                  <p className="muted">
                    Use this portal to follow student progress, inspect lab outcomes, and verify platform readiness before demos.
                  </p>
                </div>
              </div>

              <div className="portal-workflow-list">
                <div>
                  <strong>1. Review class activity</strong>
                  <p>Start with total sessions, completion rate, average score, and pass rate.</p>
                </div>

                <div>
                  <strong>2. Inspect student details</strong>
                  <p>Open the Students tab to review individual session history, score trend, and weak topics.</p>
                </div>

                <div>
                  <strong>3. Check system status</strong>
                  <p>Use System Readiness before live demos to confirm Docker, Containerlab, Web CLI, and PostgreSQL visibility.</p>
                </div>
              </div>
            </section>

            <SystemReadinessSummary
              runtimeReadiness={runtimeReadiness}
              databaseReadiness={databaseReadiness}
              isRuntimeReadinessLoading={isRuntimeReadinessLoading}
              isDatabaseReadinessLoading={isDatabaseReadinessLoading}
              runtimeReadinessError={runtimeReadinessError}
              databaseReadinessError={databaseReadinessError}
              systemStatus={systemStatus}
            />
          </div>
        </div>
      )}

      {activeTab === "students" && (
        <div className="instructor-portal-shell">
          {errorMessage && (
            <>
              <MessageBox
                type="error"
                title="Student analytics could not be loaded"
                message={errorMessage}
              />

              {errorDetails && (
                <div className="technical-detail-box">
                  <strong>Diagnostics</strong>
                  <p>{errorDetails}</p>
                </div>
              )}
            </>
          )}

          {forceCloseMessage && (
            <MessageBox
              type="info"
              title="Lab force close completed"
              message={forceCloseMessage}
            />
          )}

          {forceCloseErrorMessage && (
            <>
              <MessageBox
                type="error"
                title="Lab could not be force closed"
                message={forceCloseErrorMessage}
              />

              {forceCloseErrorDetails && (
                <div className="technical-detail-box">
                  <strong>Diagnostics</strong>
                  <p>{forceCloseErrorDetails}</p>
                </div>
              )}
            </>
          )}

          <div className="instructor-dashboard-v2">
            <StudentListPanel
              students={students}
              selectedStudentId={selectedStudentId}
              onSelectStudent={setSelectedStudentId}
              isLoading={isStudentsLoading}
            />

            <section className="instructor-student-detail">
              {!selectedStudentId && !isStudentsLoading && (
                <section className="card">
                  <AnalyticsEmptyState
                    title="Select a student."
                    message="Choose a student from the list to inspect analytics."
                  />
                </section>
              )}

              {selectedStudentId && (
                <>
                  <section className="card selected-student-header">
                    <div className="selected-student-header-main">
                      <div>
                        <span className="muted">Selected Student</span>
                        <h3>{selectedStudentId}</h3>
                        <p className="muted">
                          Last activity: {formatDateTime(selectedStudent?.last_activity_at || summary?.last_activity_at)}
                        </p>
                      </div>

                      <div className="selected-student-header-actions">
                        <button
                          className="secondary-button"
                          onClick={() => loadStudentDetails(selectedStudentId)}
                          disabled={isStudentDetailLoading}
                          type="button"
                        >
                          {isStudentDetailLoading ? "Refreshing..." : "Refresh Student"}
                        </button>

                        {isStudentDetailLoading && (
                          <span className="badge neutral">Loading details...</span>
                        )}
                      </div>
                    </div>

                    <StudentSummaryCards summary={summary} compact />
                  </section>

                  <StudentDetailTabs
                    activeTab={studentDetailTab}
                    onChange={setStudentDetailTab}
                  />

                  {studentDetailTab === "overview" && (
                    <StudentDetailOverview
                      sessions={sessions}
                      topicWeaknesses={topicWeaknesses}
                      closingSessionId={forceCloseSessionId}
                      onForceCloseLab={handleForceCloseLab}
                    />
                  )}

                  {studentDetailTab === "sessions" && (
                    <StudentSessionsTable sessions={sessions} />
                  )}

                  {studentDetailTab === "weaknesses" && (
                    <StudentTopicWeaknesses topicWeaknesses={topicWeaknesses} />
                  )}

                  {studentDetailTab === "scoreTrend" && (
                    <StudentScoreTrend scoreTrend={scoreTrend} />
                  )}
                </>
              )}
            </section>
          </div>
        </div>
      )}

      {activeTab === "analytics" && (
        <div className="instructor-portal-shell">
          {globalErrorMessage && (
            <>
              <MessageBox
                type="error"
                title="Analytics could not be loaded"
                message={globalErrorMessage}
              />

              {globalErrorDetails && (
                <div className="technical-detail-box">
                  <strong>Diagnostics</strong>
                  <p>{globalErrorDetails}</p>
                </div>
              )}
            </>
          )}

          {isGlobalAnalyticsLoading && (
            <MessageBox
              type="info"
              title="Refreshing analytics"
              message="Instructor analytics are being updated."
            />
          )}

          <div className="analytics-detail-shell">
            <AnalyticsSummaryCards summary={globalSummary} />

            <AnalyticsDetailTabs
              activeTab={analyticsDetailTab}
              onChange={setAnalyticsDetailTab}
            />

            {analyticsDetailTab === "difficulty" && (
              <DifficultyDistributionChart distribution={difficultyDistribution} />
            )}

            {analyticsDetailTab === "weaknesses" && (
              <TopicWeaknessList topicWeaknesses={globalTopicWeaknesses} />
            )}

            {analyticsDetailTab === "recentSessions" && (
              <RecentSessionsTable sessions={recentSessions} />
            )}
          </div>
        </div>
      )}

      {activeTab === "system" && (
        <div className="instructor-portal-shell">
          <SystemReadinessSummary
            runtimeReadiness={runtimeReadiness}
            databaseReadiness={databaseReadiness}
            isRuntimeReadinessLoading={isRuntimeReadinessLoading}
            isDatabaseReadinessLoading={isDatabaseReadinessLoading}
            runtimeReadinessError={runtimeReadinessError}
            databaseReadinessError={databaseReadinessError}
            systemStatus={systemStatus}
          />

          <div className="demo-readiness-grid">
            <RuntimeReadinessCard
              readiness={runtimeReadiness}
              isLoading={isRuntimeReadinessLoading}
              errorMessage={runtimeReadinessError}
              errorDetails={runtimeReadinessErrorDetails}
              lastCheckedAt={runtimeReadinessCheckedAt}
              onRefresh={loadRuntimeReadiness}
            />

            <DatabaseReadinessCard
              readiness={databaseReadiness}
              isLoading={isDatabaseReadinessLoading}
              errorMessage={databaseReadinessError}
              errorDetails={databaseReadinessErrorDetails}
              lastCheckedAt={databaseReadinessCheckedAt}
              onRefresh={loadDatabaseReadiness}
            />
          </div>
        </div>
      )}
    </>
  );
}

export default InstructorDashboardPage;
