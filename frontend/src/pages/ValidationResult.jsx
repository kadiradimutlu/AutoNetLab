import { useMemo, useState } from "react";
import ValidationSummary from "../components/ValidationSummary";
import RecommendationCard from "../components/RecommendationCard";
import MessageBox from "../components/MessageBox";
import {
  finishLab,
  getErrorDetails,
  getErrorMessage,
  getLab,
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

function isRuntimeInactiveStatus(status) {
  const normalizedStatus = String(status || "").toLowerCase();

  return (
    normalizedStatus.includes("finished") ||
    normalizedStatus.includes("destroyed") ||
    normalizedStatus.includes("error")
  );
}

function ValidationResult({ labSession, onLabUpdated, onNavigate }) {
  const [activeTab, setActiveTab] = useState("summary");
  const [validationResult, setValidationResult] = useState(null);
  const [isValidating, setIsValidating] = useState(false);
  const [isFinishingLab, setIsFinishingLab] = useState(false);
  const [infoMessage, setInfoMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [errorDetails, setErrorDetails] = useState("");

  const recommendationCount = useMemo(
    () => getRecommendationCount(validationResult),
    [validationResult]
  );

  const effectiveStatus = isRuntimeInactiveStatus(labSession?.status)
    ? labSession.status
    : validationResult?.status || labSession?.status || "";
  const isLabInactive = isRuntimeInactiveStatus(effectiveStatus);
  const hasValidationResult = Boolean(validationResult);
  const resultPassed = validationResult?.passed === true;

  async function refreshLabSession() {
    if (!labSession?.session_id) {
      return null;
    }

    const refreshedLab = await getLab(labSession.session_id);

    if (onLabUpdated) {
      onLabUpdated(refreshedLab);
    }

    return refreshedLab;
  }

  async function handleValidate() {
    if (!labSession) {
      setErrorMessage("Open or create a lab session before running validation.");
      setErrorDetails("");
      return;
    }

    setIsValidating(true);
    setInfoMessage("");
    setErrorMessage("");
    setErrorDetails("");

    try {
      const result = await validateLab(labSession.session_id);
      setValidationResult(result);
      setActiveTab("summary");
      setInfoMessage("Validation completed. You can return to the workspace, fix issues in Web CLI, and validate again.");
      await refreshLabSession();
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Validation failed. Please try again."));
      setErrorDetails(getErrorDetails(error));
      console.error("Validation failed.", error);
    } finally {
      setIsValidating(false);
    }
  }

  async function handleFinishLab() {
    if (!labSession?.session_id) {
      return;
    }

    const shouldFinish = window.confirm(
      "Finish this lab? Running containers will be stopped, but validation history and results will be preserved."
    );

    if (!shouldFinish) {
      return;
    }

    setIsFinishingLab(true);
    setInfoMessage("");
    setErrorMessage("");
    setErrorDetails("");

    try {
      await finishLab(labSession.session_id);
      await refreshLabSession();
      setInfoMessage("Lab finished successfully. Running containers were stopped and validation history was preserved.");
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Lab could not be finished."));
      setErrorDetails(getErrorDetails(error));
      console.error("Lab finish failed.", error);
    } finally {
      setIsFinishingLab(false);
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
              and receive learning recommendations. Validation does not close the running lab.
            </p>
          </div>

          <div className="actions validation-results-actions">
            <button
              className="primary-button"
              onClick={handleValidate}
              disabled={isValidating || isFinishingLab || !labSession || isLabInactive}
              type="button"
            >
              {isValidating ? "Validating..." : "Run Validation"}
            </button>

            <button
              className="secondary-button"
              onClick={() => onNavigate("workspace")}
              type="button"
            >
              Return to Workspace
            </button>

            <button
              className="danger-button"
              onClick={handleFinishLab}
              disabled={isValidating || isFinishingLab || !labSession || isLabInactive}
              type="button"
            >
              {isFinishingLab ? "Finishing..." : "Finish Lab"}
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
              <strong>{formatStatus(effectiveStatus)}</strong>
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

        {!isLabInactive && (
          <MessageBox
            type="info"
            title="Continue after validation"
            message="After validation, the running containers stay active. Return to the workspace to fix issues and validate again, or finish the lab when you are done."
          />
        )}

        {isLabInactive && (
          <MessageBox
            type="info"
            title="Lab is finished"
            message="This lab is no longer running. Validation history remains available, but Web CLI is closed."
          />
        )}

        {hasValidationResult && (
          <MessageBox
            type={resultPassed ? "success" : "info"}
            title={resultPassed ? "All checks passed" : "Continue troubleshooting"}
            message={
              resultPassed
                ? "All checks passed. You can finish the lab or return to the workspace to review your configuration."
                : "Some checks still need work. Return to the workspace, update the live configuration in Web CLI, and run validation again."
            }
          />
        )}

        {infoMessage && (
          <MessageBox
            type="success"
            title="Lab updated"
            message={infoMessage}
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
