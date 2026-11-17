# 0003. Plain SQL migrations with a small runner

- Status: accepted
- Date: 2026-11-18

## Context

The database schema will change in several steps (chunks now, embeddings next, a full-text
column later). Changes must be versioned in Git, reviewed like code and applied the same way
locally, in CI and in any deployed environment.

## Decision

Keep each schema change as a numbered SQL file in `db/migrations/`. A small runner
(`python -m app.cli migrate`) applies pending files in order, each in its own transaction,
and records them in a `schema_migrations` table. A PostgreSQL advisory lock stops two
processes from migrating at the same time. In Docker Compose, a one-shot `migrate` service
runs before the API starts.

## Alternatives considered

- **Alembic.** The standard tool for SQLAlchemy projects, with autogeneration and downgrade
  scripts. This project does not use SQLAlchemy, and the schema is small; plain SQL is easier
  to read and to explain.
- **Running DDL at application start-up.** No history, and several API replicas would race
  each other.
- **Only `db/init/` scripts.** These run once, when the database volume is created, so later
  changes would never reach an existing database.

## Consequences

- Migrations are plain SQL, using PostgreSQL features (pgvector, constraints) directly.
- No automatic downgrades: a mistake is fixed with a new migration.
- Applied files must never be edited; the runner tracks them by name, not by content.
