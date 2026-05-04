import { useLanguage } from "../hooks/useLanguage";

function RecommendationCard({ recommendations = [] }) {
  const { t } = useLanguage();

  const safeRecommendations = Array.isArray(recommendations)
    ? recommendations
    : [recommendations];

  if (!safeRecommendations.length) {
    return (
      <section className="card">
        <h3>{t("recommendation")}</h3>
        <p className="muted">{t("recommendationEmpty")}</p>
      </section>
    );
  }

  return (
    <section className="card">
      <h3>{t("recommendation")}</h3>

      <div className="recommendation-list">
        {safeRecommendations.map((recommendation, index) => {
          const isObject =
            recommendation !== null && typeof recommendation === "object";

          const topic = isObject
            ? recommendation.topic
            : `${t("recommendationNumber")} ${index + 1}`;

          const priority = isObject ? recommendation.priority : "medium";
          const message = isObject ? recommendation.message : String(recommendation);
          const relatedErrorType = isObject
            ? recommendation.related_error_type
            : "general";

          return (
            <div className="list-item" key={`${topic}-${index}`}>
              <div className="result-title-row">
                <strong>{topic}</strong>
                <span className="badge">{priority}</span>
              </div>

              <p>{message}</p>

              <p className="muted">
                Related Error Type: {relatedErrorType}
              </p>
            </div>
          );
        })}
      </div>
    </section>
  );
}

export default RecommendationCard;