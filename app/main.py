"""HTTP entry point."""

import logging
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status

from app.config import Settings, get_settings
from app.db import check_database

logger = logging.getLogger(__name__)

app = FastAPI(title="FinDoc Assistant", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness: the process is up. Does not touch any dependency."""
    return {"status": "ok"}


@app.get("/health/ready")
def ready(settings: Annotated[Settings, Depends(get_settings)]) -> dict[str, str]:
    """Readiness: the service can reach everything it needs to answer requests."""
    try:
        check_database(settings.database_url)
    except Exception as exc:
        logger.warning("readiness check failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database unavailable",
        ) from exc
    return {"status": "ready"}
