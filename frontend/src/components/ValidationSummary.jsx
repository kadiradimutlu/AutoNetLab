import MessageBox from "./MessageBox";
import ValidationCheckList from "./ValidationCheckList";
import { useLanguage } from "../hooks/useLanguage";
import {
  getValidationStatusClass,
  getValidationStatusLabel
} from "../utils/formatters";

function isCheckPassed(check) {
  const status = String(check.status || "").toLowerCase();

  if (status.includes("pass") || status === "success") {
    return true;
  }

  if (status.includes("fail") || status === "error") {
    return false;
  }

  return Boolean(check.passed);
}

function getSafeNumber(value, fallback = 0) {
  const numericValue = Number(value);

  if (Number.isNaN(numericValue)) {
    return fallback;
  }

  return numericValue;
}

function getScore(validationResult, checks) {
  if (validationResult.score !== undefined && validationResult.score !== null) {
    return getSafeNumber(validationResult.score);
  }

  const earnedPoints = checks.reduce(
    (total, check) => total + getSafeNumber(check.points),
    0
  );
  const maxPoints = checks.reduce(
    (total, check) => total + getSafeNumber(check.max_points ?? check.maxPoints),
    0
  );

  if (!maxPoints) {
    return 0;
  }

  return Math.round((earnedPoints / maxPoints) * 100);
}

function ValidationSummary({
  validationResult,
  isValidating,
  showDebugEvidence = false
}) {
  const { t } = useLanguage();

  if (isValidating) {
    return (
      <section className="card">
        <h3>{t("validationResultTitle")}</h3>
        <MessageBox
          type="info"
          title={t("validationRunningTitle")}
          message={t("validationRunningMessage")}
        />
      </section>
    );
  }

  if (!validationResult) {
    return (
      <section className="card">
        <h3>{t("validationResultTitle")}</h3>
        <MessageBox
          type="empty"
          title={t("noValidationTitle")}
          message={t("noValidationMessage")}
        />
      </section>
    );
  }

  const checks = Array.isArray(validationResult.checks)
    ? validationResult.checks
    : [];

  const totalChecks = validationResult.total_checks ?? checks.length;
  const passedChecks =
    validationResult.passed_checks ??
    checks.filter((check) => isCheckPassed(check)).length;
  const failedChecks = Math.max(totalChecks - passedChecks, 0);

  const score = getScore(validationResult, checks);
  const safeScore = Math.min(Math.max(score, 0), 100);

  return (
    <section className="card validation-summary-card">
      <div className="section-title-row">
        <div>
          <h3>{t("validationSummary")}</h3>
          <p className="muted">
            Student-safe validation result, topic grouping, points, and learning hints for the current lab session.
          </p>
        </div>

        <span className={`badge ${getValidationStatusClass(validationResult)}`}>
          {getValidationStatusLabel(validationResult)}
        </span>
      </div>

      <MessageBox
        type="info"
        title="Student-safe result view"
        message="This view hides injected errors, exact fixes, expected state, observed debug evidence, and solution details."
      />

      <div className="validation-status-panel">
        <div>
          <h4>
            {validationResult.passed
              ? "All checks passed"
              : "Some checks failed"}
          </h4>

          <p className="muted">
            Review failed topics and use the general hints before running validation again.
          </p>
        </div>

        <div className="score-area">
          <span className="muted">Score</span>
          <div className="score-box">{safeScore}/100</div>
          <div className="score-progress">
            <div
              className="score-progress-fill"
              style={{ width: `${safeScore}%` }}
            />
          </div>
        </div>
      </div>

      <div className="validation-metrics">
        <div className="metric-card">
          <span>{t("totalChecks")}</span>
          <strong>{totalChecks}</strong>
        </div>

        <div className="metric-card metric-pass">
          <span>{t("passedChecks")}</span>
          <strong>{passedChecks}</strong>
        </div>

        <div className="metric-card metric-fail">
          <span>{t("failedChecks")}</span>
          <strong>{failedChecks}</strong>
        </div>
      </div>

      <h4>Validation Checks</h4>

      <ValidationCheckList
        checks={checks}
        showDebugEvidence={showDebugEvidence}
      />
    </section>
  );
}

export default ValidationSummary;
