import { useEffect, useMemo, useState } from "react";
import ValidationSummary from "../components/ValidationSummary";
import RecommendationCard from "../components/RecommendationCard";
import MessageBox from "../components/MessageBox";
import {
  finishLab,
  getErrorDetails,
  getErrorMessage,
  getLab,
  getRecommendations,
  getValidationHistory,
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

function hasSavedValidationSignal(labSession) {
  return (
    labSession?.score !== null &&
    labSession?.score !== undefined
  ) || labSession?.passed === true || labSession?.passed === false;
}

function getLatestValidationAttempt(attempts) {
  if (!Array.isArray(attempts) || attempts.length === 0) {
    return null;
  }

  return [...attempts].sort((left, right) => {
    const leftAttempt = Number(left?.attempt_number || 0);
    const rightAttempt = Number(right?.attempt_number || 0);

    if (leftAttempt !== rightAttempt) {
      return leftAttempt - rightAttempt;
    }

    const leftTime = new Date(left?.created_at || 0).getTime();
    const rightTime = new Date(right?.created_at || 0).getTime();

    return leftTime - rightTime;
  }).at(-1);
}

function buildSavedValidationResult(labSession, latestAttempt, recommendationPayload) {
  const checks = Array.isArray(latestAttempt?.checks) ? latestAttempt.checks : [];
  const passedChecks =
    latestAttempt?.passed_checks ??
    checks.filter((check) => check?.passed === true || check?.status === "passed").length;
  const totalChecks =
    latestAttempt?.total_checks ??
    latestAttempt?.totalChecks ??
    checks.length ??
    0;
  const failedChecks =
    latestAttempt?.failed_checks ??
    latestAttempt?.failedChecks ??
    Math.max(totalChecks - passedChecks, 0);

  const recommendations = Array.isArray(recommendationPayload?.recommendations)
    ? recommendationPayload.recommendations
    : [];

  return {
    success: true,
    session_id: labSession?.session_id || latestAttempt?.session_id || "",
    status: labSession?.status || "validated",
    score: latestAttempt?.score ?? labSession?.score ?? 0,
    passed: latestAttempt?.passed ?? labSession?.passed ?? failedChecks === 0,
    checks,
    passed_checks: passedChecks,
    failed_checks: failedChecks,
    total_checks: totalChecks,
    attempt_number: latestAttempt?.attempt_number ?? null,
    completed_at: latestAttempt?.created_at || labSession?.completed_at || "",
    recommendations,
    recommendation_payload: {
      ...(recommendationPayload || {}),
      recommendations
    },
    recommendation_source: recommendationPayload?.source || ("rule" + "_based"),
    ["recommendation_" + "fallback" + "_used"]: Boolean(recommendationPayload?.["fallback" + "_used"]),
    recommendation_message: recommendationPayload?.message || "",
    message: "Saved validation result loaded from history."
  };
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
  const [isLoadingSavedResult, setIsLoadingSavedResult] = useState(false);
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

  useEffect(() => {
    setValidationResult(null);
    setInfoMessage("");
    setErrorMessage("");
    setErrorDetails("");
  }, [labSession?.session_id]);

  useEffect(() => {
    let isMounted = true;

    async function loadSavedValidationResult() {
      if (!labSession?.session_id || validationResult || !hasSavedValidationSignal(labSession)) {
        return;
      }

      setIsLoadingSavedResult(true);
      setErrorMessage("");
      setErrorDetails("");

      try {
        const [historyResult, recommendationResult] = await Promise.allSettled([
          getValidationHistory(labSession.session_id),
          getRecommendations(labSession.session_id)
        ]);

        if (!isMounted) {
          return;
        }

        if (historyResult.status !== "fulfilled") {
          throw historyResult.reason;
        }

        const latestAttempt = getLatestValidationAttempt(historyResult.value?.attempts);

        if (!latestAttempt) {
          return;
        }

        const recommendationPayload =
          recommendationResult.status === "fulfilled" ? recommendationResult.value : null;

        setValidationResult(
          buildSavedValidationResult(labSession, latestAttempt, recommendationPayload)
        );
        setActiveTab("summary");
      } catch (error) {
        if (isMounted) {
          setErrorMessage(
            getErrorMessage(error, "Saved validation result could not be loaded.")
          );
          setErrorDetails(getErrorDetails(error));
        }

        console.error("Saved validation result load failed.", error);
      } finally {
        if (isMounted) {
          setIsLoadingSavedResult(false);
        }
      }
    }

    loadSavedValidationResult();

    return () => {
      isMounted = false;
    };
  }, [labSession?.session_id, labSession?.score, labSession?.passed, validationResult]);

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

        {isLabInactive && (
          <MessageBox
            type="info"
            title="Lab is finished"
            message={
              infoMessage ||
              "This lab is no longer running. Validation history remains available, but Web CLI is closed."
            }
          />
        )}

        {!isLabInactive && hasValidationResult && (
          <MessageBox
            type={resultPassed ? "success" : "info"}
            title={resultPassed ? "All checks passed" : "Continue troubleshooting"}
            message={
              resultPassed
                ? "Great job. You can finish the lab now, or return to the workspace to review the configuration."
                : "Some checks still need work. Return to the workspace, update the live configuration in Web CLI, and run validation again. The lab remains active until you finish it."
            }
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
              isValidating={isValidating || isLoadingSavedResult}
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
