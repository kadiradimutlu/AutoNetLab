import MessageBox from "./MessageBox";
import { useLanguage } from "../hooks/useLanguage";
import {
  getCheckStatusClass,
  getCheckStatusLabel,
  getValidationStatusClass,
  getValidationStatusLabel
} from "../utils/formatters";

function getDisplayValue(value) {
  if (value === undefined || value === null || value === "") {
    return "-";
  }

  if (typeof value === "object") {
    return JSON.stringify(value);
  }

  return String(value);
}

function getCheckTitle(check, index) {
  return (
    check.topic ||
    check.check_type ||
    check.type ||
    check.check_id ||
    `Check ${index + 1}`
  );
}

function getCheckType(check) {
  return check.check_type || check.type || check.category || "-";
}

function getCheckDevice(check) {
  return check.device || check.device_name || check.node || "-";
}

function getCheckMessage(check) {
  return (
    check.message ||
    check.description ||
    (check.passed
      ? "This check passed successfully."
      : "This check failed. Please review the expected and actual values.")
  );
}

function ValidationSummary({ validationResult, isValidating }) {
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
    checks.filter((check) => check.passed).length;
  const failedChecks = Math.max(totalChecks - passedChecks, 0);
  const failedCheckList = checks.filter((check) => !check.passed);

  const score = Number(validationResult.score ?? 0);
  const safeScore = Math.min(Math.max(score, 0), 100);

  return (
    <section className="card validation-summary-card">
      <div className="section-title-row">
        <div>
          <h3>{t("validationSummary")}</h3>
          <p className="muted">
            Validation result, score, and check details for the current lab session.
          </p>
        </div>

        <span className={`badge ${getValidationStatusClass(validationResult)}`}>
          {getValidationStatusLabel(validationResult)}
        </span>
      </div>

      <div className="validation-status-panel">
        <div>
          <h4>
            {validationResult.passed
              ? "All checks passed"
              : "Some checks failed"}
          </h4>

          <p className="muted">
            This panel shows which checks passed, which checks failed, and which areas
            should be reviewed by the student.
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

      {failedCheckList.length > 0 && (
        <>
          <h4>Failed Checks</h4>

          <div className="result-list failed-check-list">
            {failedCheckList.map((check, index) => (
              <div
                className="list-item check-card failed-check-card"
                key={`failed-${check.check_id || index}`}
              >
                <div className="result-title-row">
                  <strong>{getCheckTitle(check, index)}</strong>
                  <span className="badge fail">FAIL</span>
                </div>

                <p className="check-message">{getCheckMessage(check)}</p>

                <div className="check-detail-grid">
                  <div>
                    <span>Check Type</span>
                    <strong>{getDisplayValue(getCheckType(check))}</strong>
                  </div>

                  <div>
                    <span>Device</span>
                    <strong>{getDisplayValue(getCheckDevice(check))}</strong>
                  </div>

                  <div>
                    <span>Expected</span>
                    <strong>{getDisplayValue(check.expected)}</strong>
                  </div>

                  <div>
                    <span>Actual</span>
                    <strong>{getDisplayValue(check.actual)}</strong>
                  </div>
                </div>

                <p className="muted">
                  {t("checkId")}: {getDisplayValue(check.check_id)}
                </p>
              </div>
            ))}
          </div>
        </>
      )}

      <h4>{t("checkDetails")}</h4>

      <div className="result-list">
        {checks.length === 0 && (
          <MessageBox
            type="empty"
            title="No check details"
            message="No checks list was found in the backend validation response."
          />
        )}

        {checks.map((check, index) => (
          <div
            className={`list-item check-card ${
              check.passed ? "passed-check-card" : "failed-check-card"
            }`}
            key={check.check_id || `${getCheckTitle(check, index)}-${index}`}
          >
            <div className="result-title-row">
              <strong>{getCheckTitle(check, index)}</strong>
              <span className={`badge ${getCheckStatusClass(check.passed)}`}>
                {getCheckStatusLabel(check.passed)}
              </span>
            </div>

            <p className="check-message">{getCheckMessage(check)}</p>

            <div className="check-detail-grid">
              <div>
                <span>Check Type</span>
                <strong>{getDisplayValue(getCheckType(check))}</strong>
              </div>

              <div>
                <span>Device</span>
                <strong>{getDisplayValue(getCheckDevice(check))}</strong>
              </div>

              <div>
                <span>Expected</span>
                <strong>{getDisplayValue(check.expected)}</strong>
              </div>

              <div>
                <span>Actual</span>
                <strong>{getDisplayValue(check.actual)}</strong>
              </div>
            </div>

            <p className="muted">
              {t("checkId")}: {getDisplayValue(check.check_id)}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}

export default ValidationSummary;