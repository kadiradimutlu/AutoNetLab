import MessageBox from "./MessageBox";

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
          message="Click the Run Validation button to generate a PASS/FAIL result and score."
        />
      </section>
    );
  }

  const statusClass = validationResult.status.toLowerCase();

  return (
    <section className="card">
      <h3>Validation Summary / Doğrulama Özeti</h3>

      <div className="validation-header">
        <span className={`badge ${statusClass}`}>
          {validationResult.status}
        </span>

        <div className="score-box">{validationResult.score}/100</div>
      </div>

      <p>{validationResult.summary}</p>

      <div className="info-row">
        <span>Total Checks</span>
        <strong>{validationResult.totalChecks}</strong>
      </div>

      <div className="info-row">
        <span>Passed Checks</span>
        <strong>{validationResult.passedChecks}</strong>
      </div>

      <div className="info-row">
        <span>Failed Checks</span>
        <strong>{validationResult.failedChecks}</strong>
      </div>

      <h4>Check Details / Kontrol Detayları</h4>

      <div className="result-list">
        {validationResult.results.map((item) => (
          <div className="list-item" key={item.checkId}>
            <div className="result-title-row">
              <strong>{item.title}</strong>
              <span className={`badge ${item.status.toLowerCase()}`}>
                {item.status}
              </span>
            </div>

            <p>{item.message}</p>
            <p className="muted">Related Topic: {item.relatedTopic}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

export default ValidationSummary;