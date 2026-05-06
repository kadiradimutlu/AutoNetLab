import { useLanguage } from "../hooks/useLanguage";

function normalizeRecommendation(recommendation, index) {
  if (typeof recommendation === "string") {
    return {
      topic: `Recommendation ${index + 1}`,
      priority: "medium",
      related_error_type: "-",
      message: recommendation
    };
  }

  if (!recommendation || typeof recommendation !== "object") {
    return {
      topic: `Recommendation ${index + 1}`,
      priority: "medium",
      related_error_type: "-",
      message: String(recommendation || "No recommendation message.")
    };
  }

  return {
    topic:
      recommendation.topic ||
      recommendation.title ||
      `Recommendation ${index + 1}`,
    priority:
      recommendation.priority ||
      recommendation.severity ||
      recommendation.level ||
      "medium",
    related_error_type:
      recommendation.related_error_type ||
      recommendation.error_type ||
      recommendation.check_type ||
      "-",
    message:
      recommendation.message ||
      recommendation.description ||
      recommendation.text ||
      "No recommendation message."
  };
}

function getPriorityClass(priority) {
  const normalizedPriority = String(priority || "").toLowerCase();

  if (normalizedPriority.includes("high")) {
    return "high-priority";
  }

  if (normalizedPriority.includes("low")) {
    return "low-priority";
  }

  return "medium-priority";
}

function RecommendationCard({ recommendations = [] }) {
  const { t } = useLanguage();

  const safeRecommendations = Array.isArray(recommendations)
    ? recommendations
    : [recommendations].filter(Boolean);

  const normalizedRecommendations = safeRecommendations.map((item, index) =>
    normalizeRecommendation(item, index)
  );

  if (!normalizedRecommendations.length) {
    return (
      <section className="card">
        <h3>{t("recommendation")}</h3>
        <MessageEmpty />
      </section>
    );
  }

  return (
    <section className="card recommendation-card">
      <div className="section-title-row">
        <div>
          <h3>{t("recommendation")}</h3>
          <p className="muted">
            Suggested study topics based on the validation result.
          </p>
        </div>
      </div>

      <div className="recommendation-list">
        {normalizedRecommendations.map((recommendation, index) => {
          const priorityClass = getPriorityClass(recommendation.priority);

          return (
            <div
              className={`list-item recommendation-item ${priorityClass}`}
              key={`${recommendation.topic}-${index}`}
            >
              <div className="result-title-row">
                <strong>{recommendation.topic}</strong>
                <span className={`badge ${priorityClass}`}>
                  {recommendation.priority}
                </span>
              </div>

              <p>{recommendation.message}</p>

              <div className="recommendation-meta">
                <span>Related Error Type</span>
                <strong>{recommendation.related_error_type}</strong>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function MessageEmpty() {
  const { t } = useLanguage();

  return (
    <p className="muted">
      {t("recommendationEmpty")} Recommendations will be displayed here after validation.
    </p>
  );
}

export default RecommendationCard;