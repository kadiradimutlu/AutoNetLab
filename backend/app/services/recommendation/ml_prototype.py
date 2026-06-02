from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from typing import Any

from app.services.network_topics import normalize_network_topic
from app.services.recommendation.ml_training_samples import get_training_samples


_MIN_CONFIDENCE = 0.42
_CRITICAL_TOPICS = {"default_gateway", "static_routing", "interface_state"}


def get_ml_status() -> dict[str, Any]:
    return {
        "available": True,
        "library": "pure-python",
        "error": None,
        "note": (
            "Lightweight supervised topic classifier trained from AutoNetLab "
            "scenario, fault, and validation signals."
        ),
    }


def predict_topic_priorities(
    feature_rows: list[dict[str, Any]],
) -> list[dict[str, Any]] | None:
    if not feature_rows:
        return None

    try:
        classifier = _TopicNaiveBayesClassifier(get_training_samples())
        results: list[dict[str, Any]] = []

        for row in feature_rows:
            if not isinstance(row, dict):
                continue

            probabilities = classifier.predict_probabilities(row)
            if not probabilities:
                continue

            row_topic = normalize_network_topic(row.get("topic"))
            selected = _select_prediction_for_row(
                row_topic=row_topic,
                probabilities=probabilities,
            )

            if selected is None:
                continue

            topic, confidence = selected

            if confidence < _MIN_CONFIDENCE:
                continue

            results.append(
                {
                    "topic": topic,
                    "priority": _priority_from_features(
                        row=row,
                        topic=topic,
                        confidence=confidence,
                    ),
                    "confidence": round(confidence, 2),
                    "signals": _public_signal_summary(row),
                }
            )

        return results or None

    except Exception:
        return None


class _TopicNaiveBayesClassifier:
    def __init__(self, training_samples: list[dict[str, Any]]) -> None:
        self._class_counts: Counter[str] = Counter()
        self._token_counts: dict[str, Counter[str]] = defaultdict(Counter)
        self._token_totals: Counter[str] = Counter()
        self._vocabulary: set[str] = set()

        self._fit(training_samples)

    def _fit(self, training_samples: list[dict[str, Any]]) -> None:
        for sample in training_samples:
            target_topic = normalize_network_topic(sample.get("target_topic"))
            if not target_topic or target_topic == "general_troubleshooting":
                continue

            tokens = _tokens_from_features(sample)
            if not tokens:
                continue

            priority = str(sample.get("priority") or "").strip().lower()
            if priority:
                tokens.extend([f"priority={priority}"] * 2)

            self._class_counts[target_topic] += 1

            for token in tokens:
                self._token_counts[target_topic][token] += 1
                self._token_totals[target_topic] += 1
                self._vocabulary.add(token)

    def predict_probabilities(self, features: dict[str, Any]) -> list[tuple[str, float]]:
        tokens = _tokens_from_features(features)
        if not tokens or not self._class_counts:
            return []

        total_samples = sum(self._class_counts.values())
        class_count = len(self._class_counts)
        vocab_size = max(len(self._vocabulary), 1)

        log_scores: dict[str, float] = {}

        for topic, count in self._class_counts.items():
            prior = math.log((count + 1) / (total_samples + class_count))
            token_total = self._token_totals[topic]
            token_scores = 0.0

            for token in tokens:
                token_count = self._token_counts[topic][token]
                token_scores += math.log((token_count + 1) / (token_total + vocab_size))

            log_scores[topic] = prior + token_scores

        max_log = max(log_scores.values())
        exp_scores = {
            topic: math.exp(score - max_log)
            for topic, score in log_scores.items()
        }
        denominator = sum(exp_scores.values()) or 1.0

        return sorted(
            (
                (topic, value / denominator)
                for topic, value in exp_scores.items()
            ),
            key=lambda item: item[1],
            reverse=True,
        )


def _select_prediction_for_row(
    *,
    row_topic: str,
    probabilities: list[tuple[str, float]],
) -> tuple[str, float] | None:
    if not probabilities:
        return None

    probability_by_topic = dict(probabilities)

    if row_topic in probability_by_topic:
        return row_topic, probability_by_topic[row_topic]

    return probabilities[0]


def _tokens_from_features(features: dict[str, Any]) -> list[str]:
    tokens: list[str] = []

    scenario_id = _normalize_text(features.get("scenario_id"))
    difficulty = _normalize_text(features.get("difficulty"))
    topic = normalize_network_topic(features.get("topic") or features.get("target_topic"))

    if scenario_id:
        tokens.extend(_expand_token("scenario", scenario_id, weight=3))

    if difficulty:
        tokens.extend(_expand_token("difficulty", difficulty, weight=1))

    if topic and topic != "general_troubleshooting":
        tokens.extend(_expand_token("topic", topic, weight=4))

    for field_name, weight in (
        ("failed_check_ids", 5),
        ("failed_topics", 5),
        ("affected_topics", 2),
        ("resolved_topics", 1),
    ):
        for value in _list_of_strings(features.get(field_name)):
            if "topic" in field_name:
                normalized = normalize_network_topic(value)
            else:
                normalized = _normalize_text(value)

            if normalized:
                tokens.extend(_expand_token(field_name, normalized, weight=weight))

    failed_count = _coerce_int(features.get("failed_count"), default=0)
    attempt_count = _coerce_int(features.get("attempt_count"), default=0)
    score_impact = _coerce_int(features.get("score_impact"), default=0)
    failure_rate = _coerce_float(features.get("failure_rate"), default=0.0)
    overall_score = _coerce_int(features.get("overall_score"), default=0)
    fault_resolution_score = _coerce_int(
        features.get("fault_resolution_score"),
        default=overall_score,
    )
    network_health_score = _coerce_int(
        features.get("network_health_score"),
        default=fault_resolution_score,
    )

    tokens.append(f"failed_count_bucket={_count_bucket(failed_count)}")
    tokens.append(f"attempt_count_bucket={_count_bucket(attempt_count)}")
    tokens.append(f"score_impact_bucket={_score_impact_bucket(score_impact)}")
    tokens.append(f"failure_rate_bucket={_failure_rate_bucket(failure_rate)}")
    tokens.append(f"fault_resolution_bucket={_score_bucket(fault_resolution_score)}")
    tokens.append(f"network_health_bucket={_score_bucket(network_health_score)}")

    if features.get("passed") is False:
        tokens.append("passed=false")

    return tokens


def _expand_token(prefix: str, value: str, weight: int) -> list[str]:
    safe_value = _normalize_text(value)
    if not safe_value:
        return []

    tokens = [f"{prefix}={safe_value}"] * max(weight, 1)

    for part in re.split(r"[^a-z0-9]+", safe_value):
        if part and len(part) >= 3:
            tokens.append(f"{prefix}:{part}")

    return tokens


def _priority_from_features(
    *,
    row: dict[str, Any],
    topic: str,
    confidence: float,
) -> str:
    failure_rate = _coerce_float(row.get("failure_rate"), default=0.0)
    failed_count = _coerce_int(row.get("failed_count"), default=0)
    score_impact = _coerce_int(row.get("score_impact"), default=0)
    overall_score = _coerce_int(row.get("overall_score"), default=0)

    if (
        failure_rate >= 80
        or failed_count >= 2
        or score_impact >= 20
        or overall_score < 65
    ):
        return "high"

    if topic in _CRITICAL_TOPICS and confidence >= 0.58 and overall_score < 85:
        return "high"

    if failure_rate >= 30 or failed_count >= 1 or score_impact >= 10 or overall_score < 90:
        return "medium"

    return "low"


def _public_signal_summary(row: dict[str, Any]) -> list[str]:
    signals: list[str] = []

    scenario_id = _normalize_text(row.get("scenario_id"))
    difficulty = _normalize_text(row.get("difficulty"))
    failed_check_ids = _list_of_strings(row.get("failed_check_ids"))

    if scenario_id:
        signals.append(f"scenario:{scenario_id}")

    if difficulty:
        signals.append(f"difficulty:{difficulty}")

    if failed_check_ids:
        signals.append("failed_checks_present")

    return signals


def _list_of_strings(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, (list, tuple, set)):
        return [
            str(item)
            for item in value
            if item is not None and str(item).strip()
        ]

    if isinstance(value, str) and value.strip():
        return [value]

    return []


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip().lower().replace(" ", "_")


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _count_bucket(value: int) -> str:
    if value <= 0:
        return "zero"

    if value == 1:
        return "one"

    if value == 2:
        return "two"

    return "many"


def _score_impact_bucket(value: int) -> str:
    if value <= 0:
        return "none"

    if value < 10:
        return "low"

    if value < 25:
        return "medium"

    return "high"


def _failure_rate_bucket(value: float) -> str:
    if value <= 0:
        return "none"

    if value < 30:
        return "low"

    if value < 70:
        return "medium"

    return "high"


def _score_bucket(value: int) -> str:
    if value <= 0:
        return "zero"

    if value < 50:
        return "low"

    if value < 80:
        return "partial"

    if value < 100:
        return "near_pass"

    return "pass"
