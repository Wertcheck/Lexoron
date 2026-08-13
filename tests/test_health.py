"""Smoke-Test fuer Prompt 02: bestaetigt nur, dass die Anwendung startet und
antwortet. Keine Fachlogik wird hier getestet (folgt erst mit den jeweiligen
spaeteren Modulen)."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_app_has_expected_title() -> None:
    assert app.title == "Kanzlei-AI-Pipeline"
