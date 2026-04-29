import MessageBox from "./MessageBox";
import {
  getCheckStatusClass,
  getCheckStatusLabel,
  getValidationStatusClass,
  getValidationStatusLabel
} from "../utils/formatters";

function ValidationSummary({ validationResult, isValidating }) {
  if (isValidating) {
    return (
      <section className="card">
        <h3>Validation / Doğrulama</h3>
        <MessageBox
          type="info"
          title="Validation is running"
          message="The system is checking the current lab session. Please wait..."
        />
      </section>
    );
  }

  if (!validationResult) {
    return (
      <section className="card">
        <h3>Validation / Doğrulama</h3>
        <MessageBox
          type="empty"
          title="No validation result yet"
          message="Click the Run Validation button to generate PASS/FAIL checks and a score."
        />
      </section>
    );
  }

  const totalChecks = validationResult.checks.length;
  const passedChecks = validationResult.checks.filter((check) => check.passed).length;
  const failedChecks = totalChecks - passedChecks;

  return (
    <section className="card">
      <h3>Validation Summary / Doğrulama Özeti</h3>

      <div className="validation-header">
        <span className={`badge ${getValidationStatusClass(validationResult)}`}>
          {getValidationStatusLabel(validationResult)}
        </span>

        <div className="score-box">{validationResult.score}/100</div>
      </div>

      <p>
        {validationResult.passed
          ? "All validation checks passed successfully."
          : "Some validation checks failed. Review the failed topics below."}
      </p>

      <div className="info-row">
        <span>Total Checks</span>
        <strong>{totalChecks}</strong>
      </div>

      <div className="info-row">
        <span>Passed Checks</span>
        <strong>{passedChecks}</strong>
      </div>

      <div className="info-row">
        <span>Failed Checks</span>
        <strong>{failedChecks}</strong>
      </div>

      <h4>Check Details / Kontrol Detayları</h4>

      <div className="result-list">
        {validationResult.checks.map((check) => (
          <div className="list-item" key={check.check_id}>
            <div className="result-title-row">
              <strong>{check.topic}</strong>
              <span className={`badge ${getCheckStatusClass(check.passed)}`}>
                {getCheckStatusLabel(check.passed)}
              </span>
            </div>

            <p>{check.message}</p>
            <p className="muted">Check ID: {check.check_id}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

export default ValidationSummary;