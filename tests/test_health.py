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
    assert app.title == "Lexono-Pipeline"


def test_settings_are_loaded_into_app_state_on_startup() -> None:
    """Prueft, dass die Konfiguration beim Start geladen wird (Prompt 03),
    ohne dass sich das Verhalten von /health nach aussen aendert."""
    with TestClient(app) as startup_client:
        response = startup_client.get("/health")
        assert response.status_code == 200
        assert hasattr(app.state, "settings")
        assert app.state.app_env == "development"
