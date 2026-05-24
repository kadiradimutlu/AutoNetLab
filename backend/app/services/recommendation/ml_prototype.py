from typing import Any


def get_ml_status() -> dict[str, Any]:
    classifier, error = _load_classifier()

    return {
        "available": classifier is not None,
        "library": "scikit-learn",
        "error": error,
        "note": (
            "ML prototype is optional. If scikit-learn is unavailable, "
            "the recommendation engine uses rule-based fallback."
        ),
    }


def predict_topic_priorities(
    feature_rows: list[dict[str, Any]],
) -> list[dict[str, Any]] | None:
    if not feature_rows:
        return None

    DecisionTreeClassifier, _ = _load_classifier()

    if DecisionTreeClassifier is None:
        return None

    try:
        model = DecisionTreeClassifier(max_depth=3, random_state=42)

        training_x = [
            [0.0, 0, 1, 100],
            [20.0, 1, 5, 85],
            [33.0, 1, 3, 75],
            [50.0, 1, 2, 65],
            [66.0, 2, 3, 45],
            [75.0, 3, 4, 35],
            [100.0, 2, 2, 0],
        ]
        training_y = [
            "low",
            "low",
            "medium",
            "medium",
            "high",
            "high",
            "high",
        ]

        model.fit(training_x, training_y)

        live_x = [
            [
                float(row["failure_rate"]),
                int(row["failed_count"]),
                int(row["attempt_count"]),
                int(row["overall_score"]),
            ]
            for row in feature_rows
        ]

        predicted_priorities = model.predict(live_x)
        probabilities = model.predict_proba(live_x)
        classes = list(model.classes_)

        results: list[dict[str, Any]] = []

        for row, priority, probability_row in zip(
            feature_rows,
            predicted_priorities,
            probabilities,
            strict=False,
        ):
            priority = str(priority)
            confidence = float(probability_row[classes.index(priority)])

            results.append(
                {
                    "topic": row["topic"],
                    "priority": priority,
                    "confidence": round(confidence, 2),
                    "source": "ml_prototype",
                }
            )

        return results

    except Exception:
        return None


def _load_classifier():
    try:
        from sklearn.tree import DecisionTreeClassifier

        return DecisionTreeClassifier, None

    except Exception as exc:
        return None, str(exc)
