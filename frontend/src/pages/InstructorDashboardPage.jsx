import { useEffect, useState } from "react";
import AnalyticsSummaryCards from "../components/AnalyticsSummaryCards";
import DifficultyDistributionChart from "../components/DifficultyDistributionChart";
import TopicWeaknessList from "../components/TopicWeaknessList";
import RecentSessionsTable from "../components/RecentSessionsTable";
import AnalyticsEmptyState from "../components/AnalyticsEmptyState";
import MessageBox from "../components/MessageBox";
import {
  getDifficultyDistribution,
  getErrorDetails,
  getErrorMessage,
  getInstructorSummary,
  getRecentSessions,
  getTopicWeaknesses
} from "../services/apiService";

function InstructorDashboardPage() {
  const [summary, setSummary] = useState(null);
  const [difficultyDistribution, setDifficultyDistribution] = useState([]);
  const [topicWeaknesses, setTopicWeaknesses] = useState([]);
  const [recentSessions, setRecentSessions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");
  const [errorDetails, setErrorDetails] = useState("");

  async function loadAnalytics() {
    setIsLoading(true);
    setErrorMessage("");
    setErrorDetails("");

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

      setSummary(summaryResponse);
      setDifficultyDistribution(difficultyResponse?.distribution || []);
      setTopicWeaknesses(topicWeaknessResponse?.topic_weaknesses || []);
      setRecentSessions(recentSessionsResponse?.recent_sessions || []);
    } catch (error) {
      setErrorMessage(
        getErrorMessage(
          error,
          "Instructor analytics could not be loaded."
        )
      );
      setErrorDetails(getErrorDetails(error));
      console.error("Instructor analytics loading failed.", error);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    loadAnalytics();
  }, []);

  const hasNoCompletedSessions =
    !isLoading &&
    !errorMessage &&
    summary &&
    Number(summary.completed_sessions || 0) === 0;

  if (isLoading) {
    return (
      <section className="card">
        <h2>Instructor Dashboard</h2>
        <p className="muted">Analytics loading...</p>
      </section>
    );
  }

  return (
    <>
      <section className="hero">
        <h2>Instructor Dashboard</h2>
        <p>
          Monitor class performance, completed lab sessions, pass rate, difficulty
          distribution, topic weaknesses, and recent student activity.
        </p>

        <div className="actions">
          <button className="secondary-button" onClick={loadAnalytics}>
            Refresh Analytics
          </button>
        </div>
      </section>

      {errorMessage && (
        <>
          <MessageBox
            type="error"
            title="Analytics could not be loaded"
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

      {!errorMessage && hasNoCompletedSessions && (
        <section className="card">
          <AnalyticsEmptyState
            title="No completed sessions yet."
            message="Summary cards are visible, but performance analytics will become meaningful after students run validation."
          />
        </section>
      )}

      {!errorMessage && (
        <>
          <AnalyticsSummaryCards summary={summary} />

          <div className="two-column analytics-main-grid">
            <DifficultyDistributionChart
              distribution={difficultyDistribution}
            />

            <TopicWeaknessList topicWeaknesses={topicWeaknesses} />
          </div>

          <RecentSessionsTable sessions={recentSessions} />
        </>
      )}
    </>
  );
}

export default InstructorDashboardPage;