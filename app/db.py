"""Database helpers."""

import psycopg


def check_database(database_url: str) -> None:
    """Raise if the database is unreachable or the pgvector extension is missing."""
    with psycopg.connect(database_url, connect_timeout=3) as conn:
        row = conn.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'").fetchone()
    if row is None:
        raise RuntimeError("pgvector extension is not installed")
