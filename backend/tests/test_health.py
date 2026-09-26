import pytest
from fastapi.testclient import TestClient

from app.core.logging import configure_logging
from app.main import create_app


def test_health_returns_ok() -> None:
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_endpoint_remains_available() -> None:
    paths = create_app().openapi()["paths"]
    assert "/health" in paths
    assert list(paths["/health"]) == ["get"]


def test_invalid_log_level_fails_clearly() -> None:
    with pytest.raises(ValueError, match="Invalid log level"):
        configure_logging("NOT_A_LEVEL")
