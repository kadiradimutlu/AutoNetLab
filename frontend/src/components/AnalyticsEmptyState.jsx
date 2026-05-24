function AnalyticsEmptyState({
  title = "No completed sessions yet.",
  message = "Analytics will appear here after students validate lab sessions."
}) {
  return (
    <div className="analytics-empty-state">
      <strong>{title}</strong>
      <p>{message}</p>
    </div>
  );
}

export default AnalyticsEmptyState;