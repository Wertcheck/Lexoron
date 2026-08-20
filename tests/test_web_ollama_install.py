"""Tests für die Ollama-Installer-/Update-Routen in
app/web/monitoring_router.py (20.08.).

`OllamaInstallerService` wird in JEDEM Test, der `/ollama-install/start`
tatsächlich auslöst, durch einen Fake ersetzt (`monkeypatch.setattr(
monitoring_module, "OllamaInstallerService", ...)`, gleiches Muster wie
`monkeypatch.setattr(schriftsatz_router_module, "get_drafting_service",
...)` beim Schriftsatz-Generator) - es findet hier NIE ein echter Download
oder eine echte UAC-Elevation statt."""

from __future__ import annotations

import time
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.main import app
from app.models.base import Base
from app.ollama_setup.service import OllamaInstallProgress
from tests.auth_test_utils import create_test_user, extract_csrf, login, seed_roles


class _FakeOllamaInstallerService:
    """Läuft in einem Hintergrund-Thread (wie der echte Service), aber ohne
    Netzwerk/Elevation. Ein kurzer `time.sleep` VOR dem ersten Fortschritts-
    Callback stellt sicher, dass der aufrufende Request-Handler zuverlässig
    zuerst den "downloading"-Zustand zurückgibt, den er selbst SYNCHRON vor
    dem Thread-Start setzt (app/web/monitoring_router.py:
    start_ollama_install) - ohne diese kleine Verzögerung wäre das Ergebnis
    von der Thread-Planung des Betriebssystems abhängig (flaky Test)."""

    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        pass

    def run_guided_install(self, on_progress) -> OllamaInstallProgress:  # noqa: ANN001
        time.sleep(0.15)
        on_progress(
            OllamaInstallProgress(status="launching", percent=100, message="Wird gestartet…")
        )
        result = OllamaInstallProgress(
            status="done", percent=100, message="Ollama ist erreichbar."
        )
        on_progress(result)
        return result


class _FakeFailingOllamaInstallerService:
    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        pass

    def run_guided_install(self, on_progress) -> OllamaInstallProgress:  # noqa: ANN001
        result = OllamaInstallProgress(
            status="error", percent=100, error="Installation wurde nicht bestätigt."
        )
        on_progress(result)
        return result


@pytest.fixture()
def db_session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture(autouse=True)
def _reset_ollama_install_progress() -> Iterator[None]:
    """`app.state.ollama_install_progress` ist wie `app.state.ollama_check`
    global auf dem EINEN `app`-Singleton abgelegt, nicht pro Test isoliert
    (dieselbe FastAPI-App-Instanz wird von der gesamten Testsuite geteilt).
    Ohne Reset könnte ein Test vom Endzustand eines vorherigen Tests
    abhängen - explizit auf "kein vorheriger Lauf" zurückgesetzt, vor UND
    nach jedem Test in dieser Datei."""
    if hasattr(app.state, "ollama_install_progress"):
        del app.state.ollama_install_progress
    yield
    if hasattr(app.state, "ollama_install_progress"):
        del app.state.ollama_install_progress


@pytest.fixture()
def client(db_session: Session) -> Iterator[TestClient]:
    def _override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def roles(db_session: Session):
    return seed_roles(db_session)


def _login_admin(client: TestClient, db_session: Session, roles) -> None:
    create_test_user(db_session, roles["admin"], "admin@kanzlei.test")
    login(client, "admin@kanzlei.test")


def _csrf(client: TestClient) -> str:
    # Bewusst NICHT /dashboard/settings (admin-only) - einige Aufrufer
    # dieser Hilfsfunktion sind als Anwalt/Mitarbeiter angemeldet, um genau
    # die Admin-Sperre der Ollama-Install-Routen zu testen. /dashboard/inbox
    # ist für alle drei Rollen lesbar und trägt denselben, sitzungsweiten
    # csrf_token (siehe app/web/router.py: inbox()).
    page = client.get("/dashboard/inbox")
    return extract_csrf(page.text)


def _wait_for_status(client: TestClient, expected: str, *, timeout_seconds: float = 2.0) -> str:
    deadline = time.monotonic() + timeout_seconds
    last_status = ""
    while time.monotonic() < deadline:
        response = client.get("/dashboard/monitoring/ollama-install/status")
        last_status = "done" if 'data-status="done"' in response.text else (
            "error" if 'data-status="error"' in response.text else "pending"
        )
        if last_status == expected:
            return last_status
        time.sleep(0.02)
    return last_status


# --- Zugriffsschutz ---


def test_start_requires_login(client: TestClient) -> None:
    # `csrf_token` muss als Formularfeld PRÄSENT sein (auch mit
    # Platzhalterwert) - `require_role`s Dependency verlangt es als
    # Pflichtfeld; fehlt es ganz, liefert FastAPI bereits vorher einen
    # eigenen 422-Validierungsfehler, statt den Login-Check überhaupt zu
    # erreichen (siehe app/auth/permissions.py: require_role).
    response = client.post(
        "/dashboard/monitoring/ollama-install/start",
        data={"csrf_token": "irrelevant-ohne-session"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "/dashboard/login" in response.headers["location"]


@pytest.mark.parametrize("role_name", ["anwalt", "mitarbeiter"])
def test_start_requires_admin_role(
    client: TestClient, db_session: Session, roles, role_name: str
) -> None:
    create_test_user(db_session, roles[role_name], f"{role_name}@kanzlei.test")
    login(client, f"{role_name}@kanzlei.test")
    csrf = _csrf(client)

    response = client.post(
        "/dashboard/monitoring/ollama-install/start", data={"csrf_token": csrf}
    )
    assert response.status_code == 403


def test_status_requires_login(client: TestClient) -> None:
    response = client.get("/dashboard/monitoring/ollama-install/status", follow_redirects=False)
    assert response.status_code == 303


# --- Ablauf (mit Fake-Service) ---


def test_start_returns_downloading_state_immediately(
    client: TestClient, db_session: Session, roles, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.web.monitoring_router as monitoring_module

    monkeypatch.setattr(monitoring_module, "OllamaInstallerService", _FakeOllamaInstallerService)
    _login_admin(client, db_session, roles)
    csrf = _csrf(client)

    response = client.post(
        "/dashboard/monitoring/ollama-install/start", data={"csrf_token": csrf}
    )

    assert response.status_code == 200
    assert 'data-status="downloading"' in response.text


def test_start_eventually_reaches_done_via_fake_service(
    client: TestClient, db_session: Session, roles, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.web.monitoring_router as monitoring_module

    monkeypatch.setattr(monitoring_module, "OllamaInstallerService", _FakeOllamaInstallerService)
    _login_admin(client, db_session, roles)
    csrf = _csrf(client)

    client.post("/dashboard/monitoring/ollama-install/start", data={"csrf_token": csrf})

    final_status = _wait_for_status(client, "done")
    assert final_status == "done"


def test_start_surfaces_declined_elevation_as_error(
    client: TestClient, db_session: Session, roles, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.web.monitoring_router as monitoring_module

    monkeypatch.setattr(
        monitoring_module, "OllamaInstallerService", _FakeFailingOllamaInstallerService
    )
    _login_admin(client, db_session, roles)
    csrf = _csrf(client)

    client.post("/dashboard/monitoring/ollama-install/start", data={"csrf_token": csrf})

    final_status = _wait_for_status(client, "error")
    assert final_status == "error"
    response = client.get("/dashboard/monitoring/ollama-install/status")
    assert "nicht bestätigt" in response.text


def test_status_before_any_start_shows_idle_state(
    client: TestClient, db_session: Session, roles
) -> None:
    _login_admin(client, db_session, roles)

    response = client.get("/dashboard/monitoring/ollama-install/status")

    assert response.status_code == 200
    assert 'data-status="idle"' in response.text


def test_second_start_while_running_does_not_start_a_duplicate(
    client: TestClient, db_session: Session, roles
) -> None:
    """Der Lock selbst wird direkt geprüft, ohne einen echten Hintergrund-
    Lauf abzuwarten - simuliert "ein Vorgang läuft bereits" durch manuelles
    Halten des Locks. `acquire(timeout=...)` statt `blocking=False`, da der
    Lock modulweit (nicht pro Test zurückgesetzt) ist - ein Hintergrund-
    Thread eines VORHERIGEN Tests könnte ihn kurzzeitig noch halten."""
    import app.web.monitoring_router as monitoring_module

    _login_admin(client, db_session, roles)
    csrf = _csrf(client)

    acquired = monitoring_module._ollama_install_lock.acquire(timeout=5)
    assert acquired, "Lock war nach vorherigen Tests nicht rechtzeitig frei"
    try:
        response = client.post(
            "/dashboard/monitoring/ollama-install/start", data={"csrf_token": csrf}
        )
        assert response.status_code == 200
        # Der Lock ist weiterhin (ausschließlich) von UNS gehalten - die
        # Route hat also keinen zweiten Hintergrund-Thread gestartet.
        assert monitoring_module._ollama_install_lock.locked()
    finally:
        monitoring_module._ollama_install_lock.release()
