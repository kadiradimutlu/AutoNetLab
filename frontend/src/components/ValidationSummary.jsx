function ValidationSummary({ validationResult }) {
  if (!validationResult) {
    return (
      <section className="card">
        <h3>Validation / Doğrulama</h3>
        <p className="muted">No validation result yet.</p>
      </section>
    );
  }

  const statusClass = validationResult.status.toLowerCase();

  return (
    <section className="card">
      <h3>Validation Summary / Doğrulama Özeti</h3>

      <span className={`badge ${statusClass}`}>
        {validationResult.status}
      </span>

      <div className="score-box">{validationResult.score}/100</div>

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

      <h4>Check Details</h4>

      <div className="result-list">
        {validationResult.results.map((item) => (
          <div className="list-item" key={item.checkId}>
            <strong>{item.title}</strong>{" "}
            <span className={`badge ${item.status.toLowerCase()}`}>
              {item.status}
            </span>
            <p>{item.message}</p>
            <p className="muted">Related Topic: {item.relatedTopic}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

export default ValidationSummary;