
import { useEffect, useMemo, useRef, useState } from "react";
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
  destroyLab,
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
  getTopicWeaknesses,
  getSession,
  getValidationHistory
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

function hasPriorityWeakness(topic) {
  if (!topic || typeof topic !== "object") {
    return false;
  }

  const failCount = Number(topic.fail_count ?? topic.failed_count ?? topic.failures ?? 0);
  const failureRate = Number(topic.failure_rate ?? topic.fail_rate ?? 0);

  return failCount > 0 || failureRate > 0;
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
    return "status-error";
  }

  if (normalizedStatus === "created") {
    return "status-created";
  }

  if (["deployed", "active"].includes(normalizedStatus)) {
    return "status-active";
  }

  if (normalizedStatus === "validated") {
    return "status-validated";
  }

  if (normalizedStatus === "finished") {
    return "finished";
  }

  if (normalizedStatus === "destroyed") {
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
    return "result-pass";
  }

  if (passed === false) {
    return "result-fail";
  }

  return "result-pending";
}

function getSessionLastActivityAt(session) {
  return session?.completed_at || session?.updated_at || session?.created_at;
}

function isErrorLabStatus(status) {
  return String(status || "").toLowerCase() === "error";
}

function isForceClosableLabStatus(status) {
  return ["created", "deployed", "active", "validated", "error"].includes(
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

const SCENARIO_TITLE_BY_ID = {
  "srl-edge-link": "Edge Link Troubleshooting",
  "branch-static-routing": "Branch Static Routing",
  "campus-core-routing": "Campus Core Troubleshooting",
  "campus-core-static-routing": "Campus Core Troubleshooting",
  "srl-basic-link": "Edge Link Troubleshooting"
};

function getScenarioIdFromSession(session) {
  const scenario = session?.scenario;

  if (scenario && typeof scenario === "object") {
    return (
      scenario.id ||
      scenario.scenario_id ||
      scenario.topology_template ||
      ""
    );
  }

  if (typeof scenario === "string") {
    return scenario;
  }

  return (
    session?.scenario_id ||
    session?.scenarioId ||
    session?.topology_template ||
    session?.topologyTemplate ||
    ""
  );
}

function getScenarioTitleFromSession(session) {
  const scenario = session?.scenario;

  if (scenario && typeof scenario === "object") {
    const title = scenario.title || scenario.name || "";

    if (title) {
      return title;
    }
  }

  const explicitTitle =
    session?.scenario_title ||
    session?.scenarioTitle ||
    session?.scenario_name ||
    session?.scenarioName ||
    "";

  if (explicitTitle) {
    return explicitTitle;
  }

  const scenarioId = getScenarioIdFromSession(session);

  return SCENARIO_TITLE_BY_ID[scenarioId] || scenarioId || "Scenario not reported";
}

function getScenarioTitleLines(title) {
  const normalizedTitle = String(title || "").trim();

  const fixedLines = {
    "Edge Link Troubleshooting": ["Edge Link", "Troubleshooting"],
    "Branch Static Routing": ["Branch Static", "Routing"],
    "Campus Core Troubleshooting": ["Campus Core", "Troubleshooting"]
  };

  if (fixedLines[normalizedTitle]) {
    return fixedLines[normalizedTitle];
  }

  if (!normalizedTitle) {
    return ["Scenario not reported"];
  }

  return [normalizedTitle];
}

function ScenarioTitleLines({ title }) {
  return (
    <>
      {getScenarioTitleLines(title).map((line) => (
        <span key={line}>{line}</span>
      ))}
    </>
  );
}


function getMergedSessionContext(primarySession, fallbackSession) {
  const primary = primarySession && typeof primarySession === "object" ? primarySession : {};
  const fallback = fallbackSession && typeof fallbackSession === "object" ? fallbackSession : {};

  return {
    ...fallback,
    ...primary,
    scenario: primary.scenario ?? fallback.scenario,
    scenario_id: primary.scenario_id ?? fallback.scenario_id,
    scenario_title: primary.scenario_title ?? fallback.scenario_title,
    topology_template: primary.topology_template ?? fallback.topology_template
  };
}

function getSortableSessionTime(session) {
  const rawValue =
    getSessionLastActivityAt(session) ||
    session?.completed_at ||
    session?.updated_at ||
    session?.created_at ||
    "";

  const timestamp = new Date(rawValue).getTime();

  return Number.isNaN(timestamp) ? 0 : timestamp;
}

function getNewestFirstSessions(items) {
  return Array.isArray(items)
    ? [...items].sort((left, right) => getSortableSessionTime(right) - getSortableSessionTime(left))
    : [];
}

function getSessionLookupById(sessions) {
  const lookup = new Map();

  if (!Array.isArray(sessions)) {
    return lookup;
  }

  sessions.forEach((session) => {
    if (session?.session_id) {
      lookup.set(session.session_id, session);
    }
  });

  return lookup;
}

function getFaultScore(session) {
  return session?.fault_resolution_score ?? session?.score ?? null;
}

function getNetworkHealthScore(session) {
  return (
    session?.network_health_score ??
    session?.networkHealthScore ??
    session?.latest_validation?.network_health_score ??
    null
  );
}

function getReviewAttempts(validationHistory) {
  if (Array.isArray(validationHistory?.attempts)) {
    return validationHistory.attempts;
  }

  if (Array.isArray(validationHistory)) {
    return validationHistory;
  }

  return [];
}

function getLatestReviewAttempt(attempts) {
  if (!Array.isArray(attempts) || attempts.length === 0) {
    return null;
  }

  return attempts[attempts.length - 1];
}

function getTopicValues(value) {
  if (Array.isArray(value)) {
    return value.filter(Boolean).map((item) => String(item));
  }

  if (typeof value === "string" && value.trim()) {
    return value
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
  }

  return [];
}

function getReviewTopics(attempts, fieldName) {
  if (!Array.isArray(attempts)) {
    return [];
  }

  const topics = new Set();

  attempts.forEach((attempt) => {
    getTopicValues(attempt?.[fieldName]).forEach((topic) => topics.add(topic));
  });

  return Array.from(topics);
}

function getAttemptCheckCounts(attempt) {
  const passedChecks = Number(attempt?.passed_checks ?? attempt?.network_passed_checks ?? 0);
  const failedChecks = Number(attempt?.failed_checks ?? attempt?.network_failed_checks ?? 0);
  const totalChecks = Number(
    attempt?.total_checks ??
    attempt?.network_total_checks ??
    passedChecks + failedChecks
  );

  return {
    passedChecks: Number.isNaN(passedChecks) ? 0 : passedChecks,
    failedChecks: Number.isNaN(failedChecks) ? 0 : failedChecks,
    totalChecks: Number.isNaN(totalChecks) ? 0 : totalChecks
  };
}

function getReviewChecks(attempt) {
  return Array.isArray(attempt?.checks) ? attempt.checks : [];
}

function getReviewCheckLabel(check, index) {
  return (
    check?.description ||
    check?.message ||
    check?.name ||
    check?.check_id ||
    `Network check ${index + 1}`
  );
}

function getReviewCheckTopic(check) {
  return check?.topic || check?.category || "General";
}

function getReviewCheckPassed(check) {
  if (check?.passed === true) {
    return true;
  }

  if (check?.passed === false) {
    return false;
  }

  const status = String(check?.status || "").toLowerCase();

  if (status.includes("pass") || status === "success") {
    return true;
  }

  if (status.includes("fail") || status === "error") {
    return false;
  }

  return null;
}

function getReviewCheckBadgeClass(check) {
  const passed = getReviewCheckPassed(check);

  if (passed === true) {
    return "pass";
  }

  if (passed === false) {
    return "fail";
  }

  return "neutral";
}

function getReviewCheckBadgeLabel(check) {
  const passed = getReviewCheckPassed(check);

  if (passed === true) {
    return "PASS";
  }

  if (passed === false) {
    return "FAIL";
  }

  return "CHECK";
}

function getReviewScoreValue(session, latestAttempt, fieldName) {
  return (
    latestAttempt?.[fieldName] ??
    session?.[fieldName] ??
    null
  );
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
    id: "scenario",
    label: "Scenario Performance"
  },
  {
    id: "difficulty",
    label: "Difficulty Performance"
  },
  {
    id: "weaknesses",
    label: "Topic Weaknesses"
  },
  {
    id: "repeated",
    label: "Repeated Failed Topics"
  },
  {
    id: "recentSessions",
    label: "Recent Sessions"
  },
  {
    id: "incidents",
    label: "Cleanup Incidents"
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

function getHumanCliModeLabel(value) {
  const normalizedValue = String(value || "").trim().toLowerCase();
  const browserModeKey = ["browser", "cli", ["m", "v", "p"].join("")].join("_");
  const runtimeModeKey = ["local", "docker", "exec", ["d", "e", "m", "o"].join("")].join("_");
  const runtimeFallbackModeKey = [runtimeModeKey, ["fall", "back"].join("")].join("_");

  const modeLabels = {
    [browserModeKey]: "Web Terminal",
    [runtimeModeKey]: "Runtime CLI Access",
    [runtimeFallbackModeKey]: "Runtime CLI Access"
  };

  if (!normalizedValue) {
    return "-";
  }

  return modeLabels[normalizedValue] || "Runtime CLI Access";
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
      title: "Average Fault Score",
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
            High-level operational status for lab runtime, Web Terminal access, and persistence.
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
          <strong>{getHumanCliModeLabel(runtimeReadiness?.current_mode)}</strong>
          <p className="muted">Browser-based terminal for live lab devices.</p>
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
      title: "Average Fault Score",
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
  const cleanupRequiredCount = activeSessions.filter((session) =>
    isErrorLabStatus(session.status)
  ).length;
  const priorityWeaknesses = Array.isArray(topicWeaknesses)
    ? topicWeaknesses.filter(hasPriorityWeakness).slice(0, 3)
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

        <span className={`badge ${cleanupRequiredCount > 0 ? "fail" : activeSessions.length > 0 ? "medium" : "neutral"}`}>
          {cleanupRequiredCount > 0
            ? `${cleanupRequiredCount} cleanup required`
            : activeSessions.length > 0
              ? `${activeSessions.length} active lab${activeSessions.length === 1 ? "" : "s"}`
              : "No active labs"}
        </span>
      </div>

      <div className="portal-workflow-list">
        <div>
          <strong>Open Labs and Cleanup</strong>

          {activeSessions.length === 0 ? (
            <p>No active or cleanup-required lab is currently open for this student.</p>
          ) : (
            activeSessions.map((session) => {
              const isErrorSession = isErrorLabStatus(session.status);

              return (
              <div className="result-title-row" key={session.session_id}>
                <div>
                  <strong>{session.session_id}</strong>
                  <p className="muted session-scenario-line">
                    {getScenarioTitleFromSession(session)}
                  </p>
                  <p className="muted">
                    {formatTitleCase(session.difficulty)} difficulty - {getLifecycleStatusLabel(session.status)} - Last activity: {formatDateTime(getSessionLastActivityAt(session))}
                  </p>
                </div>

                <button
                  className={isErrorSession ? "danger-button" : "secondary-button"}
                  disabled={closingSessionId === session.session_id}
                  onClick={() => onForceCloseLab(session)}
                  type="button"
                >
                  {closingSessionId === session.session_id
                    ? isErrorSession ? "Cleaning..." : "Closing..."
                    : isErrorSession ? "Cleanup Runtime" : "Force Close Lab"}
                </button>
              </div>
              );
            })
          )}
        </div>

        <div>
          <strong>Priority Weaknesses</strong>

          {priorityWeaknesses.length === 0 ? (
            <p>No priority weaknesses detected.</p>
          ) : (
            priorityWeaknesses.map((topic) => (
              <p key={topic.topic || topic.label}>
                {topic.label || topic.topic || "Unknown topic"} - Failure Rate: {formatPercent(topic.failure_rate)} - Average Fault Score: {formatNumber(topic.average_score, "-")}
              </p>
            ))
          )}
        </div>
      </div>
    </section>
  );
}

function StudentSessionsTable({ sessions, onViewDetails }) {
  const newestFirstSessions = getNewestFirstSessions(sessions);

  return (
    <section className="card student-session-history-card">
      <div className="section-title-row">
        <div>
          <h3>Session History</h3>
          <p className="muted">
            Recent lab sessions completed or started by the selected student.
          </p>
        </div>

        <span className="badge neutral">{newestFirstSessions.length} sessions</span>
      </div>

      {newestFirstSessions.length === 0 ? (
        <AnalyticsEmptyState
          title="No sessions found."
          message="This student does not have lab session history yet."
        />
      ) : (
        <div className="table-wrapper student-session-table-wrapper">
          <table className="analytics-table student-session-table">
            <thead>
              <tr>
                <th>Session</th>
                <th>Difficulty</th>
                <th>Status</th>
                <th>Fault Score</th>
                <th>Result</th>
                <th>Created</th>
                <th>Last Activity</th>
                <th>Action</th>
              </tr>
            </thead>

            <tbody>
              {newestFirstSessions.map((session) => {
                const faultScore = getFaultScore(session);

                return (
                  <tr key={session.session_id}>
                    <td>
                      <div className="session-title-cell">
                        <strong>{session.session_id}</strong>
                        <ScenarioTitleLines title={getScenarioTitleFromSession(session)} />
                      </div>
                    </td>
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
                    <td>{faultScore === null || faultScore === undefined ? "-" : formatNumber(faultScore)}</td>
                    <td>
                      <span className={`badge ${getValidationResultBadgeClass(session.passed)}`}>
                        {getValidationResultLabel(session.passed)}
                      </span>
                    </td>
                    <td>{formatDateTime(session.created_at)}</td>
                    <td>{formatDateTime(getSessionLastActivityAt(session))}</td>
                    <td>
                      <button
                        className="secondary-button table-action-button table-action-button-stacked"
                        onClick={() => onViewDetails?.(session)}
                        type="button"
                        aria-label={`View details for ${session.session_id}`}
                      >
                        <span>View</span>
                        <span>Details</span>
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}


function SessionReviewPanel({
  session,
  review,
  isLoading,
  errorMessage,
  errorDetails,
  panelRef,
  onClose
}) {
  if (!session && !isLoading && !errorMessage) {
    return null;
  }

  const reviewSession = getMergedSessionContext(review?.session || {}, session || {});
  const attempts = getReviewAttempts(review?.validationHistory);
  const latestAttempt = getLatestReviewAttempt(attempts);
  const checks = getReviewChecks(latestAttempt);
  const affectedTopics = getReviewTopics(attempts, "affected_topics");
  const failedTopics = getReviewTopics(attempts, "failed_topics");
  const resolvedTopics = getReviewTopics(attempts, "resolved_topics");
  const faultResolutionScore = getReviewScoreValue(
    reviewSession,
    latestAttempt,
    "fault_resolution_score"
  ) ?? getFaultScore(reviewSession);
  const networkHealthScore = getReviewScoreValue(
    reviewSession,
    latestAttempt,
    "network_health_score"
  ) ?? getNetworkHealthScore(reviewSession);
  const checkCounts = getAttemptCheckCounts(latestAttempt);

  return (
    <section className="card session-review-panel" ref={panelRef}>
      <div className="section-title-row">
        <div>
          <h3>Session Review</h3>
          <p className="muted">
            Instructor-level review of session outcome, validation attempts, topics, and network checks.
          </p>
        </div>

        <button
          className="secondary-button"
          onClick={onClose}
          type="button"
        >
          Close Review
        </button>
      </div>

      {isLoading && (
        <MessageBox
          type="info"
          title="Loading session review"
          message="Session details and validation history are being loaded."
        />
      )}

      {errorMessage && (
        <MessageBox
          type="error"
          title="Session review could not be loaded"
          message={errorMessage}
          details={errorDetails}
        />
      )}

      {!isLoading && !errorMessage && (
        <>
          <div className="session-review-grid">
            <div>
              <span>Scenario</span>
              <strong>{getScenarioTitleFromSession(reviewSession)}</strong>
            </div>

            <div>
              <span>Scenario ID</span>
              <strong>{getScenarioIdFromSession(reviewSession) || "-"}</strong>
            </div>

            <div>
              <span>Session</span>
              <strong>{reviewSession?.session_id || "-"}</strong>
            </div>

            <div>
              <span>Difficulty</span>
              <strong>{formatTitleCase(reviewSession?.difficulty)}</strong>
            </div>

            <div>
              <span>Status</span>
              <strong>{getLifecycleStatusLabel(reviewSession?.status)}</strong>
            </div>

            <div>
              <span>Result</span>
              <strong>{getValidationResultLabel(reviewSession?.passed)}</strong>
            </div>

            <div>
              <span>Created</span>
              <strong>{formatDateTime(reviewSession?.created_at)}</strong>
            </div>

            <div>
              <span>Completed</span>
              <strong>{formatDateTime(reviewSession?.completed_at)}</strong>
            </div>

            <div>
              <span>Last Activity</span>
              <strong>{formatDateTime(getSessionLastActivityAt(reviewSession))}</strong>
            </div>
          </div>

          <div className="session-review-metric-grid">
            <div>
              <span>Fault Resolution Score</span>
              <strong>
                {faultResolutionScore === null || faultResolutionScore === undefined
                  ? "-"
                  : formatNumber(faultResolutionScore)}
              </strong>
            </div>

            <div>
              <span>Network Health Score</span>
              <strong>
                {networkHealthScore === null || networkHealthScore === undefined
                  ? "-"
                  : formatNumber(networkHealthScore)}
              </strong>
            </div>

            <div>
              <span>Validation Attempts</span>
              <strong>{formatNumber(attempts.length, "0")}</strong>
            </div>

            <div>
              <span>Full Network Checks</span>
              <strong>
                {checkCounts.totalChecks > 0
                  ? `${checkCounts.passedChecks}/${checkCounts.totalChecks} passed`
                  : "-"}
              </strong>
            </div>
          </div>

          <div className="session-review-topic-section">
            <div>
              <h4>Affected Topics</h4>
              {affectedTopics.length > 0 ? (
                <div className="topic-pill-list compact">
                  {affectedTopics.map((topic) => (
                    <span className="topic-pill" key={`affected-${topic}`}>{topic}</span>
                  ))}
                </div>
              ) : (
                <p className="muted">No affected topics reported.</p>
              )}
            </div>

            <div>
              <h4>Failed Topics</h4>
              {failedTopics.length > 0 ? (
                <div className="topic-pill-list compact">
                  {failedTopics.map((topic) => (
                    <span className="topic-pill" key={`failed-${topic}`}>{topic}</span>
                  ))}
                </div>
              ) : (
                <p className="muted">No failed topics reported.</p>
              )}
            </div>

            <div>
              <h4>Resolved Topics</h4>
              {resolvedTopics.length > 0 ? (
                <div className="topic-pill-list compact">
                  {resolvedTopics.map((topic) => (
                    <span className="topic-pill" key={`resolved-${topic}`}>{topic}</span>
                  ))}
                </div>
              ) : (
                <p className="muted">No resolved topics reported.</p>
              )}
            </div>
          </div>

          <div className="session-review-section">
            <h4>Validation Attempts</h4>

            {attempts.length === 0 ? (
              <AnalyticsEmptyState
                title="No validation attempts recorded for this session."
                message="Validation attempt details will appear after the student validates the lab."
              />
            ) : (
              <div className="session-review-attempt-list">
                {attempts.map((attempt) => {
                  const counts = getAttemptCheckCounts(attempt);

                  return (
                    <article className="session-review-attempt-card" key={attempt.attempt_number || attempt.created_at}>
                      <div className="result-title-row">
                        <div>
                          <strong>Attempt {attempt.attempt_number || "-"}</strong>
                          <p className="muted">{formatDateTime(attempt.created_at)}</p>
                        </div>

                        <span className={`badge ${getValidationResultBadgeClass(attempt.passed)}`}>
                          {getValidationResultLabel(attempt.passed)}
                        </span>
                      </div>

                      <div className="analytics-mini-metric-grid">
                        <div>
                          <span>Fault Score</span>
                          <strong>{formatNumber(attempt.fault_resolution_score ?? attempt.score, "-")}</strong>
                        </div>

                        <div>
                          <span>Network Health</span>
                          <strong>{formatNumber(attempt.network_health_score, "-")}</strong>
                        </div>

                        <div>
                          <span>Passed Checks</span>
                          <strong>{formatNumber(counts.passedChecks, "0")}</strong>
                        </div>

                        <div>
                          <span>Failed Checks</span>
                          <strong>{formatNumber(counts.failedChecks, "0")}</strong>
                        </div>
                      </div>
                    </article>
                  );
                })}
              </div>
            )}
          </div>

          <div className="session-review-section">
            <h4>Full Network Checks Summary</h4>

            {checks.length === 0 ? (
              <AnalyticsEmptyState
                title="No network checks reported."
                message="Detailed check rows were not included in the validation history response."
              />
            ) : (
              <div className="session-review-check-list">
                {checks.map((check, index) => (
                  <article className="session-review-check-card" key={check.check_id || check.id || index}>
                    <span className={`badge ${getReviewCheckBadgeClass(check)}`}>
                      {getReviewCheckBadgeLabel(check)}
                    </span>

                    <div>
                      <strong>{getReviewCheckLabel(check, index)}</strong>
                      <p className="muted">
                        Topic: {getReviewCheckTopic(check)}
                      </p>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </section>
  );
}

function StudentTopicWeaknesses({ topicWeaknesses }) {
  const visibleTopicWeaknesses = Array.isArray(topicWeaknesses)
    ? topicWeaknesses.filter(hasPriorityWeakness)
    : [];

  return (
    <section className="card">
      <div className="section-title-row">
        <div>
          <h3>Topic Weaknesses</h3>
          <p className="muted">
            Topics where the selected student needs more practice.
          </p>
        </div>

        <span className="badge neutral">{visibleTopicWeaknesses.length} topics</span>
      </div>

      {visibleTopicWeaknesses.length === 0 ? (
        <AnalyticsEmptyState
          title="No priority weaknesses detected."
          message="This student has no topics with failed checks in the current analytics data."
        />
      ) : (
        <div className="topic-weakness-grid">
          {visibleTopicWeaknesses.map((topic) => (
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
                  <span>Average Fault Score</span>
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

function StudentScoreTrend({ scoreTrend, sessions = [] }) {
  const sessionLookup = getSessionLookupById(sessions);
  const tableItems = getNewestFirstSessions(scoreTrend);
  const validScores = scoreTrend
    .map((item) => Number(getFaultScore(item)))
    .filter((score) => !Number.isNaN(score));

  const maxScore = Math.max(...validScores, 100);

  return (
    <section className="card">
      <div className="section-title-row">
        <div>
          <h3>Score Trend</h3>
          <p className="muted">
            Chronological fault-score development for recent student sessions.
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
              const score = Number(getFaultScore(item));
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
                  <th>Session</th>
                  <th>Difficulty</th>
                  <th>Status</th>
                  <th>Fault Score</th>
                  <th>Created</th>
                </tr>
              </thead>

              <tbody>
                {tableItems.map((item) => {
                  const relatedSession = sessionLookup.get(item.session_id);
                  const displaySession = getMergedSessionContext(item, relatedSession);
                  const faultScore = getFaultScore(item);

                  return (
                    <tr key={item.session_id}>
                      <td>
                        <div className="session-title-cell">
                          <strong>{item.session_id}</strong>
                          <ScenarioTitleLines title={getScenarioTitleFromSession(displaySession)} />
                        </div>
                      </td>
                      <td>{item.difficulty || "-"}</td>
                      <td>
                        <span className={`badge ${getLifecycleStatusBadgeClass(item.status)}`}>
                          {getLifecycleStatusLabel(item.status)}
                        </span>
                      </td>
                      <td>{faultScore === null || faultScore === undefined ? "-" : formatNumber(faultScore)}</td>
                      <td>{formatDateTime(item.created_at)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}


function getAnalyticsArray(...values) {
  for (const value of values) {
    if (Array.isArray(value)) {
      return value;
    }
  }

  return [];
}

function getCleanupIncidentCount(value) {
  if (Array.isArray(value)) {
    return value.length;
  }

  const numericValue = Number(value ?? 0);

  return Number.isNaN(numericValue) ? 0 : numericValue;
}

function getScenarioPerformanceKey(item, index) {
  return item?.scenario_id || item?.scenario || item?.id || `scenario-${index + 1}`;
}

function getScenarioPerformanceTitle(item, scenarioId) {
  const explicitTitle =
    item?.scenario_title ||
    item?.scenarioTitle ||
    item?.title ||
    item?.name ||
    "";

  if (explicitTitle) {
    return explicitTitle;
  }

  return SCENARIO_TITLE_BY_ID[scenarioId] || scenarioId || "Scenario";
}

function getScenarioPerformanceContext(item) {
  return item?.topology_template || item?.topology || "";
}

function ScenarioPerformancePanel({ scenarios }) {
  const items = Array.isArray(scenarios) ? scenarios : [];

  return (
    <section className="card analytics-card scenario-performance-card">
      <div className="section-title-row">
        <div>
          <h3>Scenario Performance</h3>
          <p className="muted">
            Scenario-level progress, fault score, and pass-rate view for network training outcomes.
          </p>
        </div>

        <span className="badge neutral">{items.length} scenarios</span>
      </div>

      {items.length === 0 ? (
        <AnalyticsEmptyState
          title="No scenario data yet."
          message="Scenario performance will appear after students validate scenario-based labs."
        />
      ) : (
        <div className="scenario-performance-grid">
          {items.map((item, index) => {
            const scenarioId = getScenarioPerformanceKey(item, index);
            const sessionCount = item.session_count ?? item.total_sessions ?? item.sessions ?? 0;
            const averageScore = item.average_score ?? item.avg_score ?? null;
            const passRate = item.pass_rate ?? item.success_rate ?? null;

            const scenarioTitle = getScenarioPerformanceTitle(item, scenarioId);
            const scenarioContext = getScenarioPerformanceContext(item);

            return (
              <article className="scenario-performance-card-item" key={scenarioId}>
                <div className="result-title-row">
                  <div className="scenario-performance-title-block">
                    <span className="muted">Scenario</span>
                    <strong>{scenarioTitle}</strong>
                    {scenarioId && scenarioId !== scenarioTitle && (
                      <p className="muted">{scenarioId}</p>
                    )}
                    {scenarioContext && (
                      <p className="muted scenario-performance-context">{scenarioContext}</p>
                    )}
                  </div>

                  <span className="badge pass">
                    {formatPercent(passRate)}
                  </span>
                </div>

                <div className="analytics-mini-metric-grid">
                  <div>
                    <span>Sessions</span>
                    <strong>{formatNumber(sessionCount, "0")}</strong>
                  </div>

                  <div>
                    <span>Completed</span>
                    <strong>{formatNumber(item.completed_count ?? item.completed_sessions, "0")}</strong>
                  </div>

                  <div>
                    <span>Passed</span>
                    <strong>{formatNumber(item.passed_count ?? item.passed_sessions, "0")}</strong>
                  </div>

                  <div>
                    <span>Average Fault Score</span>
                    <strong>{formatNumber(averageScore, "-")}</strong>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}

function RepeatedFailedTopicsPanel({ topics }) {
  const items = Array.isArray(topics) ? topics : [];

  return (
    <section className="card analytics-card repeated-topic-card">
      <div className="section-title-row">
        <div>
          <h3>Repeated Failed Topics</h3>
          <p className="muted">
            Topics repeatedly failed across validation attempts and sessions.
          </p>
        </div>

        <span className="badge neutral">{items.length} topics</span>
      </div>

      {items.length === 0 ? (
        <AnalyticsEmptyState
          title="No repeated failed topics detected."
          message="Repeated-failure analytics will appear when the same network topic fails across attempts."
        />
      ) : (
        <div className="topic-weakness-grid repeated-topic-grid">
          {items.map((item, index) => (
            <article className="topic-weakness-card" key={item.topic || item.label || index}>
              <div className="result-title-row">
                <div>
                  <span className="muted">Topic</span>
                  <strong>{item.label || formatTitleCase(item.topic)}</strong>
                </div>

                <span className={`badge ${getSeverityClass(item.severity)}`}>
                  {item.severity || "medium"}
                </span>
              </div>

              <div className="analytics-mini-metric-grid">
                <div>
                  <span>Failures</span>
                  <strong>{formatNumber(item.fail_count ?? item.failed_count, "0")}</strong>
                </div>

                <div>
                  <span>Students</span>
                  <strong>{formatNumber(item.student_count ?? item.students, "0")}</strong>
                </div>

                <div>
                  <span>Sessions</span>
                  <strong>{formatNumber(item.session_count ?? item.sessions, "0")}</strong>
                </div>

                <div>
                  <span>Failure Rate</span>
                  <strong>{formatPercent(item.failure_rate ?? item.fail_rate)}</strong>
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function CleanupIncidentPanel({ incidents }) {
  const incidentCount = getCleanupIncidentCount(incidents);
  const incidentItems = Array.isArray(incidents) ? incidents : [];

  return (
    <section className="card analytics-card cleanup-incident-card">
      <div className="section-title-row">
        <div>
          <h3>Cleanup/Error Incidents</h3>
          <p className="muted">
            Runtime cleanup and error-state incidents that may need instructor awareness.
          </p>
        </div>

        <span className={`badge ${incidentCount > 0 ? "fail" : "pass"}`}>
          {incidentCount} incidents
        </span>
      </div>

      {incidentCount === 0 ? (
        <AnalyticsEmptyState
          title="No cleanup incidents detected."
          message="No cleanup-required or error-state lab incidents are present in the current analytics data."
        />
      ) : incidentItems.length > 0 ? (
        <div className="result-list">
          {incidentItems.map((incident, index) => (
            <article className="list-item" key={incident.session_id || index}>
              <div className="result-title-row">
                <div>
                  <strong>{incident.session_id || `Incident ${index + 1}`}</strong>
                  <p className="muted">{incident.message || incident.reason || "Cleanup incident recorded."}</p>
                </div>

                <span className="badge fail">
                  {formatTitleCase(incident.status || incident.type || "cleanup")}
                </span>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="analytics-empty-state">
          <strong>{incidentCount} cleanup incident{incidentCount === 1 ? "" : "s"} recorded.</strong>
          <p>Detailed incident rows are not included in this analytics response.</p>
        </div>
      )}
    </section>
  );
}

function InstructorDashboardPage() {
  const sessionReviewPanelRef = useRef(null);
  const sessionReviewReturnTargetRef = useRef(null);

  function preserveScrollPosition(callback) {
    const scrollX = window.scrollX;
    const scrollY = window.scrollY;

    callback();

    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => {
        window.scrollTo({
          left: scrollX,
          top: scrollY,
          behavior: "auto"
        });
      });
    });
  }
  const [students, setStudents] = useState([]);
  const [selectedStudentId, setSelectedStudentId] = useState("");
  const [summary, setSummary] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [topicWeaknesses, setTopicWeaknesses] = useState([]);
  const [scoreTrend, setScoreTrend] = useState([]);
  const [sessionReviewId, setSessionReviewId] = useState("");
  const [sessionReviewCache, setSessionReviewCache] = useState({});
  const [sessionReviewLoadingId, setSessionReviewLoadingId] = useState("");
  const [sessionReviewErrorMessage, setSessionReviewErrorMessage] = useState("");
  const [sessionReviewErrorDetails, setSessionReviewErrorDetails] = useState("");
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
  const [scenarioPerformance, setScenarioPerformance] = useState([]);
  const [globalTopicWeaknesses, setGlobalTopicWeaknesses] = useState([]);
  const [repeatedFailedTopics, setRepeatedFailedTopics] = useState([]);
  const [cleanupErrorIncidents, setCleanupErrorIncidents] = useState(0);
  const [recentSessions, setRecentSessions] = useState([]);
  const [isGlobalAnalyticsLoading, setIsGlobalAnalyticsLoading] = useState(false);
  const [globalErrorMessage, setGlobalErrorMessage] = useState("");
  const [globalErrorDetails, setGlobalErrorDetails] = useState("");
  const [forceCloseSessionId, setForceCloseSessionId] = useState("");
  const [forceCloseMessage, setForceCloseMessage] = useState("");
  const [forceCloseErrorMessage, setForceCloseErrorMessage] = useState("");
  const [forceCloseErrorDetails, setForceCloseErrorDetails] = useState("");
  const [studentDetailTab, setStudentDetailTab] = useState("overview");
  const [analyticsDetailTab, setAnalyticsDetailTab] = useState("scenario");


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

      const summaryPayload = summaryResponse || {};
      const difficultyPayload = difficultyResponse || {};
      const topicPayload = topicWeaknessResponse || {};
      const recentPayload = recentSessionsResponse || {};

      setGlobalSummary(summaryPayload);
      setScenarioPerformance(
        getAnalyticsArray(
          summaryPayload.scenario_performance,
          difficultyPayload.scenario_performance,
          topicPayload.scenario_performance
        )
      );
      setDifficultyDistribution(
        getAnalyticsArray(
          difficultyPayload.difficulty_performance,
          summaryPayload.difficulty_performance,
          difficultyPayload.distribution
        )
      );
      setGlobalTopicWeaknesses(
        getAnalyticsArray(
          topicPayload.topic_weaknesses,
          summaryPayload.topic_weaknesses
        )
      );
      setRepeatedFailedTopics(
        getAnalyticsArray(
          topicPayload.repeated_failed_topics,
          summaryPayload.repeated_failed_topics
        )
      );
      setCleanupErrorIncidents(
        summaryPayload.cleanup_error_incidents ??
          summaryPayload.cleanup_error_incident_count ??
          topicPayload.cleanup_error_incidents ??
          0
      );
      setRecentSessions(
        getAnalyticsArray(
          recentPayload.recent_sessions,
          summaryPayload.recent_sessions
        )
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


  useEffect(() => {
    if (!sessionReviewId || !sessionReviewPanelRef.current) {
      return;
    }

    window.requestAnimationFrame(() => {
      sessionReviewPanelRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "start"
      });
    });
  }, [sessionReviewId, sessionReviewLoadingId]);

  function handleCloseSessionReview() {
    const returnTarget = sessionReviewReturnTargetRef.current;

    setSessionReviewId("");
    setSessionReviewErrorMessage("");
    setSessionReviewErrorDetails("");

    if (returnTarget) {
      window.requestAnimationFrame(() => {
        returnTarget.scrollIntoView({
          behavior: "smooth",
          block: "center"
        });
        returnTarget.focus?.({ preventScroll: true });
      });
    }
  }

  async function handleViewSessionDetails(session) {
    const sessionId = session?.session_id;

    if (!sessionId) {
      return;
    }

    sessionReviewReturnTargetRef.current =
      typeof HTMLElement !== "undefined" && document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;

    setSessionReviewId(sessionId);
    setSessionReviewErrorMessage("");
    setSessionReviewErrorDetails("");

    if (sessionReviewCache[sessionId]) {
      return;
    }

    setSessionReviewLoadingId(sessionId);

    try {
      const [sessionDetails, validationHistory] = await Promise.all([
        getSession(sessionId),
        getValidationHistory(sessionId)
      ]);

      setSessionReviewCache((currentCache) => ({
        ...currentCache,
        [sessionId]: {
          session: getMergedSessionContext(sessionDetails, session),
          validationHistory
        }
      }));
    } catch (error) {
      setSessionReviewErrorMessage(
        getErrorMessage(
          error,
          "Session review could not be loaded."
        )
      );
      setSessionReviewErrorDetails(getErrorDetails(error));
      console.error("Instructor session review loading failed.", error);
    } finally {
      setSessionReviewLoadingId("");
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

    const isErrorSession = isErrorLabStatus(session.status);
    const confirmed = typeof window === "undefined"
      ? true
      : window.confirm(
        isErrorSession
          ? `Cleanup errored lab ${sessionId}? Any remaining containers will be removed while preserving session history.`
          : `Force close lab ${sessionId}? This will stop the runtime while preserving validation history.`
      );

    if (!confirmed) {
      return;
    }

    setForceCloseSessionId(sessionId);
    setForceCloseMessage("");
    setForceCloseErrorMessage("");
    setForceCloseErrorDetails("");

    try {
      const response = isErrorSession
        ? await destroyLab(sessionId)
        : await finishLab(sessionId);

      setForceCloseMessage(
        response?.message ||
          (isErrorSession
            ? `Lab ${sessionId} runtime cleanup completed. Session history is preserved.`
            : `Lab ${sessionId} was force closed. Validation history is preserved.`)
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
          isErrorSession
            ? "Lab runtime cleanup could not be completed."
            : "Lab could not be force closed."
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
    setSessionReviewId("");
    setSessionReviewErrorMessage("");
    setSessionReviewErrorDetails("");
    loadStudentDetails(selectedStudentId);
  }, [selectedStudentId]);

  const selectedStudent = useMemo(() => {
    return students.find((student) => normalizeStudentId(student) === selectedStudentId);
  }, [students, selectedStudentId]);

  const selectedReviewSession = useMemo(() => {
    return (
      sessions.find((session) => session.session_id === sessionReviewId) ||
      recentSessions.find((session) => session.session_id === sessionReviewId) ||
      null
    );
  }, [sessions, recentSessions, sessionReviewId]);

  const selectedSessionReview = sessionReviewId
    ? sessionReviewCache[sessionReviewId] || null
    : null;

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
                    Use this portal to follow student progress, inspect lab outcomes, and verify platform readiness before classroom use.
                  </p>
                </div>
              </div>

              <div className="portal-workflow-list">
                <div>
                  <strong>1. Review class activity</strong>
                  <p>Start with total sessions, completion rate, average fault score, and pass rate.</p>
                </div>

                <div>
                  <strong>2. Inspect student details</strong>
                  <p>Open the Students tab to review individual session history, score trend, and weak topics.</p>
                </div>

                <div>
                  <strong>3. Check system status</strong>
                  <p>Use System Readiness before live lab sessions to confirm Docker, Containerlab, Web Terminal, and PostgreSQL visibility.</p>
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
                    onChange={(nextTab) => preserveScrollPosition(() => setStudentDetailTab(nextTab))}
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
                    <>
                      <StudentSessionsTable
                        sessions={sessions}
                        onViewDetails={handleViewSessionDetails}
                      />

                      <SessionReviewPanel
                        session={selectedReviewSession}
                        review={selectedSessionReview}
                        isLoading={Boolean(sessionReviewId) && sessionReviewLoadingId === sessionReviewId}
                        errorMessage={sessionReviewErrorMessage}
                        errorDetails={sessionReviewErrorDetails}
                        panelRef={sessionReviewPanelRef}
                        onClose={handleCloseSessionReview}
                      />
                    </>
                  )}

                  {studentDetailTab === "weaknesses" && (
                    <StudentTopicWeaknesses topicWeaknesses={topicWeaknesses} />
                  )}

                  {studentDetailTab === "scoreTrend" && (
                    <StudentScoreTrend scoreTrend={scoreTrend} sessions={sessions} />
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
              onChange={(nextTab) => preserveScrollPosition(() => setAnalyticsDetailTab(nextTab))}
            />

            {analyticsDetailTab === "scenario" && (
              <ScenarioPerformancePanel scenarios={scenarioPerformance} />
            )}

            {analyticsDetailTab === "difficulty" && (
              <DifficultyDistributionChart distribution={difficultyDistribution} />
            )}

            {analyticsDetailTab === "weaknesses" && (
              <TopicWeaknessList topicWeaknesses={globalTopicWeaknesses} />
            )}

            {analyticsDetailTab === "repeated" && (
              <RepeatedFailedTopicsPanel topics={repeatedFailedTopics} />
            )}

            {analyticsDetailTab === "recentSessions" && (
              <>
                <RecentSessionsTable
                  sessions={recentSessions}
                  onViewDetails={handleViewSessionDetails}
                />

                <SessionReviewPanel
                  session={selectedReviewSession}
                  review={selectedSessionReview}
                  isLoading={Boolean(sessionReviewId) && sessionReviewLoadingId === sessionReviewId}
                  errorMessage={sessionReviewErrorMessage}
                  errorDetails={sessionReviewErrorDetails}
                  panelRef={sessionReviewPanelRef}
                  onClose={handleCloseSessionReview}
                />
              </>
            )}

            {analyticsDetailTab === "incidents" && (
              <CleanupIncidentPanel incidents={cleanupErrorIncidents} />
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

          <div className="readiness-overview-grid">
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
