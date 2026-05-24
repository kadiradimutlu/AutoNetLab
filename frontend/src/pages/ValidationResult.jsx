import { useMemo, useState } from "react";
import ValidationSummary from "../components/ValidationSummary";
import RecommendationCard from "../components/RecommendationCard";
import MessageBox from "../components/MessageBox";
import {
  getErrorDetails,
  getErrorMessage,
  validateLab
} from "../services/apiService";
import {
  formatDifficulty,
  formatStatus
} from "../utils/formatters";

function getRecommendationCount(validationResult) {
  const recommendations =
    validationResult?.recommendations ||
    validationResult?.recommendation_payload?.recommendations ||
    [];

  return Array.isArray(recommendations) ? recommendations.length : 0;
}

function ValidationResult({ labSession, onNavigate }) {
  const [activeTab, setActiveTab] = useState("summary");
  const [validationResult, setValidationResult] = useState(null);
  const [isValidating, setIsValidating] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [errorDetails, setErrorDetails] = useState("");

  const recommendationCount = useMemo(
    () => getRecommendationCount(validationResult),
    [validationResult]
  );

  async function handleValidate() {
    if (!labSession) {
      setErrorMessage("Open or create a lab session before running validation.");
      setErrorDetails("");
      return;
    }

    setIsValidating(true);
    setErrorMessage("");
    setErrorDetails("");

    try {
      const result = await validateLab(labSession.session_id);
      setValidationResult(result);
      setActiveTab("summary");
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Validation failed. Please try again."));
      setErrorDetails(getErrorDetails(error));
      console.error("Validation failed.", error);
    } finally {
      setIsValidating(false);
    }
  }

  return (
    <div className="validation-results-page">
      <section className="card validation-results-header">
        <div className="section-title-row validation-results-title-row">
          <div>
            <h2>Validation Results</h2>
            <p className="muted">
              Run validation to check the current lab configuration, review your score,
              and receive learning recommendations.
            </p>
          </div>

          <div className="actions validation-results-actions">
            <button
              className="primary-button"
              onClick={handleValidate}
              disabled={isValidating || !labSession}
              type="button"
            >
              {isValidating ? "Validating..." : "Run Validation"}
            </button>

            <button
              className="secondary-button"
              onClick={() => onNavigate("workspace")}
              type="button"
            >
              Back to Workspace
            </button>

            <button
              className="secondary-button"
              onClick={() => onNavigate("myLabs")}
              type="button"
            >
              My Labs
            </button>
          </div>
        </div>

        {labSession ? (
          <div className="validation-compact-summary">
            <div>
              <span>Lab ID</span>
              <strong>{labSession.session_id}</strong>
            </div>

            <div>
              <span>Difficulty</span>
              <strong>{formatDifficulty(labSession.difficulty)}</strong>
            </div>

            <div>
              <span>Status</span>
              <strong>{formatStatus(labSession.status)}</strong>
            </div>

            <div>
              <span>Recommendations</span>
              <strong>{recommendationCount}</strong>
            </div>
          </div>
        ) : (
          <MessageBox
            type="info"
            title="No lab selected"
            message="Create a new lab or open a saved lab from My Labs before running validation."
          />
        )}

        {errorMessage && (
          <>
            <MessageBox
              type="error"
              title="Validation failed"
              message={errorMessage}
            />

            {errorDetails && (
              <details className="technical-detail-box">
                <summary>Show diagnostics</summary>
                <p>{errorDetails}</p>
              </details>
            )}
          </>
        )}
      </section>

      <section className="card validation-results-tabs-card">
        <div className="result-tab-list" role="tablist" aria-label="Validation result sections">
          <button
            className={activeTab === "summary" ? "active" : ""}
            type="button"
            role="tab"
            aria-selected={activeTab === "summary"}
            onClick={() => setActiveTab("summary")}
          >
            Summary
          </button>

          <button
            className={activeTab === "recommendations" ? "active" : ""}
            type="button"
            role="tab"
            aria-selected={activeTab === "recommendations"}
            onClick={() => setActiveTab("recommendations")}
          >
            Recommendations
            {recommendationCount > 0 && (
              <span className="tab-count">{recommendationCount}</span>
            )}
          </button>
        </div>

        <div className="result-tab-panel">
          {activeTab === "summary" && (
            <ValidationSummary
              validationResult={validationResult}
              isValidating={isValidating}
            />
          )}

          {activeTab === "recommendations" && (
            <RecommendationCard
              recommendationData={validationResult}
              recommendations={validationResult?.recommendations || []}
            />
          )}
        </div>
      </section>
    </div>
  );
}

export default ValidationResult;
