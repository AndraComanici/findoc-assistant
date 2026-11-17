"""A minimal schema migration runner.

Each file in the migrations directory is a plain SQL script named ``NNNN_description.sql``.
Files are applied in name order, each in its own transaction, and recorded in
``schema_migrations`` so they run exactly once per database.
"""

import logging
from pathlib import Path

import psycopg

logger = logging.getLogger(__name__)

# Arbitrary constant: any two processes running migrations take the same lock.
_LOCK_ID = 7_391_002


def pending_files(migrations_dir: Path, applied: set[str]) -> list[Path]:
    files = sorted(migrations_dir.glob("*.sql"))
    return [f for f in files if f.stem not in applied]


def migrate(database_url: str, migrations_dir: Path) -> list[str]:
    """Apply pending migrations and return the versions that were applied."""
    applied_now: list[str] = []
    with psycopg.connect(database_url, autocommit=True) as conn:
        # A session-level advisory lock stops two containers from migrating at the same time.
        conn.execute("SELECT pg_advisory_lock(%s)", (_LOCK_ID,))
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version    TEXT PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
            applied = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
            for path in pending_files(migrations_dir, applied):
                with conn.transaction():
                    conn.execute(path.read_text(encoding="utf-8"))
                    conn.execute(
                        "INSERT INTO schema_migrations (version) VALUES (%s)", (path.stem,)
                    )
                logger.info("applied migration %s", path.name)
                applied_now.append(path.stem)
        finally:
            conn.execute("SELECT pg_advisory_unlock(%s)", (_LOCK_ID,))
    return applied_now
