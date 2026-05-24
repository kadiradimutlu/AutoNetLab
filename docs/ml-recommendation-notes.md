# Sprint 7 ML Recommendation Notes

This document explains the Sprint 7 recommendation module / öneri modülü scope.

## Goal

Sprint 7 improves the recommendation module by adding:

- explanatory recommendation output
- priority / confidence fields
- topic performance data
- ML-ready session history
- optional machine learning prototype / makine öğrenmesi prototipi
- rule-based fallback / kural tabanlı yedek sistem

## Current approach

The validation result remains the source of truth.

After validation, the backend stores topic-level performance data inside the session metadata:

- topic
- label
- attempt_count
- passed_count
- fail_count
- failure_rate
- topic_score
- failed_checks

This makes the session history easier to use for future analytics and ML experiments.

## ML prototype

The ML prototype is intentionally small and optional.

If scikit-learn is installed, the backend can use a tiny DecisionTreeClassifier trained on synthetic/demo data to estimate recommendation priority.

If scikit-learn is not installed or the model fails, the backend automatically uses rule-based fallback.

## Reliability rule

The rule-based fallback is always preserved.

The recommendation endpoint must not fail just because the ML prototype is unavailable.

## Limitation statement

Due to limited real student data, ML model is implemented as a prototype and rule-based fallback is used for reliability.

## Source values

- rule_based: deterministic recommendation rules based on validation checks
- ml_prototype: optional ML prototype output
- hybrid: rule-based validation signals combined with ML prototype output

## Out of scope

This sprint does not include:

- production-grade ML training pipeline
- large dataset collection
- LMS integration
- authentication
- advanced OSPF/BGP scenarios
- cloud ML deployment

## Frontend contract notes

Frontend should display:

- topic label
- reason
- explanation
- priority
- confidence
- source
- next actions
- related failed checks

If recommendations are empty, frontend should show an empty/fallback state and ask the student to run validation first.
