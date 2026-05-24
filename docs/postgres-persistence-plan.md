# AutoNetLab PostgreSQL Persistence Plan

Sprint 16 introduces a PostgreSQL-ready persistence layer.

## Production target

- PostgreSQL
- SQLAlchemy ORM
- Alembic migrations

## Local development fallback

Local development and tests can use SQLite through:

```env
DATABASE_URL=sqlite:///./autonetlab_dev.db
```

## Planned migration path

1. Add SQLAlchemy models and Alembic migration infrastructure.
2. Add database readiness endpoint.
3. Keep existing `session.json` persistence as the compatibility fallback.
4. Write lab session metadata to PostgreSQL and `session.json` together.
5. Move instructor analytics reads to PostgreSQL with file fallback.
6. Keep Containerlab runtime artifacts in `containerlab/generated`.

## Core tables

- `users`
- `lab_sessions`
- `validation_results`
- `recommendations`

## Principle

The database stores metadata, analytics, validation outcomes, and recommendation history.

Containerlab runtime artifacts and generated topology files remain filesystem-based.

## Sprint 16 dual-write step

The next persistence step writes session metadata, validation results, and recommendation payloads to the database while preserving the existing `session.json` fallback.

The dual-write approach keeps the current runtime stable:

- Lab generation and Containerlab artifacts remain filesystem-based.
- `session.json` remains the compatibility fallback.
- PostgreSQL receives structured metadata for analytics and future reporting.
- Database persistence is best-effort during this step; a database write failure must not break lab deploy, validation, or Web CLI flows.


## Sprint 17 PostgreSQL-backed analytics

Sprint 17 moves instructor analytics to a DB-first model.

Analytics now read from PostgreSQL-backed session metadata first. If the database
is unavailable or returns no session records, the previous `session.json` reader
is preserved as a compatibility fallback.

This keeps the API contract stable while making these instructor views use
persistent data:

- analytics summary
- difficulty distribution
- topic weaknesses
- recent sessions
- student list
- student summary
- student sessions
- student topic weaknesses
- student score trend


Sprint 21 contract freeze note

Sprint 21 does not require a new database migration.

The existing persistence model already stores the fields needed by the frontend lab history contract:

lab_sessions.score
lab_sessions.passed
lab_sessions.created_at
lab_sessions.completed_at
lab_sessions.topology_json

Sprint 21 exposes these values through frontend-ready API responses while preserving PostgreSQL DB-first analytics and session.json fallback behavior.
