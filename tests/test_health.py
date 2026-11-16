import pytest
from fastapi.testclient import TestClient

from app import main

client = TestClient(main.app)


def test_health_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_returns_ready_when_database_is_reachable(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(main, "check_database", lambda url: None)

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_ready_returns_503_when_database_is_down(monkeypatch: pytest.MonkeyPatch):
    def fail(url: str) -> None:
        raise ConnectionError("connection refused")

    monkeypatch.setattr(main, "check_database", fail)

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "database unavailable"}
