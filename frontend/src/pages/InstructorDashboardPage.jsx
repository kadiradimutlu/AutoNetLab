import { useEffect, useMemo, useState } from "react";
import AnalyticsEmptyState from "../components/AnalyticsEmptyState";
import MessageBox from "../components/MessageBox";
import RuntimeReadinessCard from "../components/RuntimeReadinessCard";
import DatabaseReadinessCard from "../components/DatabaseReadinessCard";
import {
  getErrorDetails,
  getErrorMessage,
  getInstructorStudentScoreTrend,
  getInstructorStudentSessions,
  getInstructorStudentSummary,
  getInstructorStudents,
  getInstructorStudentTopicWeaknesses,
  getRuntimeReadiness,
  getDatabaseReadiness
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

function getStatusBadgeClass(status, passed) {
  const normalizedStatus = String(status || "").toLowerCase();

  if (passed === true || normalizedStatus.includes("pass")) {
    return "pass";
  }

  if (passed === false || normalizedStatus.includes("fail") || normalizedStatus.includes("error")) {
    return "fail";
  }

  if (normalizedStatus.includes("active") || normalizedStatus.includes("deployed")) {
    return "medium";
  }

  return "neutral";
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

function StudentSummaryCards({ summary }) {
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
    },
    {
      title: "Last Activity",
      value: formatDateTime(summary?.last_activity_at)
    }
  ];

  return (
    <section className="student-summary-grid">
      {cards.map((card) => (
        <div className="metric-card" key={card.title}>
          <span>{card.title}</span>
          <strong>{card.value}</strong>
        </div>
      ))}
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
                <th>Passed</th>
                <th>Created</th>
                <th>Completed</th>
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
                  <td>{session.status || "-"}</td>
                  <td>{session.score === null || session.score === undefined ? "-" : formatNumber(session.score)}</td>
                  <td>
                    <span className={`badge ${getStatusBadgeClass(session.status, session.passed)}`}>
                      {session.passed === true ? "PASS" : session.passed === false ? "FAIL" : "N/A"}
                    </span>
                  </td>
                  <td>{formatDateTime(session.created_at)}</td>
                  <td>{formatDateTime(session.completed_at)}</td>
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
                    <td>{item.status || "-"}</td>
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
    loadRuntimeReadiness();
    loadDatabaseReadiness();
    loadStudents();
  }, []);

  useEffect(() => {
    loadStudentDetails(selectedStudentId);
  }, [selectedStudentId]);

  const selectedStudent = useMemo(() => {
    return students.find((student) => normalizeStudentId(student) === selectedStudentId);
  }, [students, selectedStudentId]);

  return (
    <>
      <section className="hero">
        <h2>Instructor Dashboard v2</h2>
        <p>
          Inspect student-level lab performance, session history, topic weaknesses,
          and score trends from instructor-only analytics endpoints.
        </p>

        <div className="actions">
          <button
            className="secondary-button"
            onClick={loadStudents}
            disabled={isStudentsLoading || isStudentDetailLoading}
          >
            {isStudentsLoading ? "Refreshing..." : "Refresh Students"}
          </button>

          {selectedStudentId && (
            <button
              className="secondary-button"
              onClick={() => loadStudentDetails(selectedStudentId)}
              disabled={isStudentDetailLoading}
            >
              {isStudentDetailLoading ? "Loading..." : "Refresh Selected Student"}
            </button>
          )}
        </div>
      </section>

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

      {errorMessage && (
        <>
          <MessageBox
            type="error"
            title="Instructor analytics could not be loaded"
            message={errorMessage}
          />

          {errorDetails && (
            <div className="technical-detail-box">
              <strong>Technical detail</strong>
              <p>{errorDetails}</p>
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
                <div>
                  <span className="muted">Selected Student</span>
                  <h3>{selectedStudentId}</h3>
                  <p className="muted">
                    Last activity: {formatDateTime(selectedStudent?.last_activity_at || summary?.last_activity_at)}
                  </p>
                </div>

                {isStudentDetailLoading && (
                  <span className="badge neutral">Loading details...</span>
                )}
              </section>

              <StudentSummaryCards summary={summary} />

              <div className="two-column instructor-detail-grid">
                <StudentTopicWeaknesses topicWeaknesses={topicWeaknesses} />
                <StudentScoreTrend scoreTrend={scoreTrend} />
              </div>

              <StudentSessionsTable sessions={sessions} />
            </>
          )}
        </section>
      </div>
    </>
  );
}

export default InstructorDashboardPage;
