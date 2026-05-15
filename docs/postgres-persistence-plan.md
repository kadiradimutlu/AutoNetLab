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