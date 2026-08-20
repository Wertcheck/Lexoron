"""Tests für app/system_health/service.py (Schritt 3, Teil 2)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.base import Base
from app.system_health.service import SystemHealthService


@pytest.fixture()
def db_session(tmp_path) -> Iterator[Session]:
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_disk_space_check_reports_free_and_total(tmp_path) -> None:
    status = SystemHealthService().check_disk_space(tmp_path)
    assert status.checked is True
    assert status.free_gb is not None
    assert status.total_gb is not None
    assert 0 <= status.percent_free <= 100


def test_disk_space_check_never_raises_on_invalid_path() -> None:
    status = SystemHealthService().check_disk_space("Z:\\this\\path\\should\\not\\exist\\???")
    assert status.checked is False
    assert status.error is not None


def test_sqlite_database_status_ok(db_session: Session, tmp_path) -> None:
    db_path = tmp_path / "test.db"
    status = SystemHealthService().check_database_status(
        db_session, f"sqlite:///{db_path}"
    )
    assert status.kind == "sqlite"
    assert status.file_exists is True
    assert status.integrity_ok is True
    assert status.size_mb is not None


def test_sqlite_database_status_missing_file(db_session: Session) -> None:
    status = SystemHealthService().check_database_status(
        db_session, "sqlite:///./this_file_does_not_exist.db"
    )
    assert status.file_exists is False
    assert status.integrity_ok is None


def test_claude_api_check_without_key_reports_not_checked() -> None:
    result = SystemHealthService().check_claude_api_reachability(None)
    assert result.checked is False
    assert result.reachable is False


def test_claude_api_check_never_raises_on_connection_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FailingModels:
        def list(self, limit: int) -> None:
            raise ConnectionError("kein Netzwerk")

    class _FailingClient:
        def __init__(self, **kwargs) -> None:
            self.models = _FailingModels()

    monkeypatch.setattr("anthropic.Anthropic", _FailingClient)

    result = SystemHealthService().check_claude_api_reachability("sk-ant-test-key")
    assert result.checked is True
    assert result.reachable is False
    assert result.error is not None


def test_claude_api_check_reports_reachable_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    class _OkModels:
        def list(self, limit: int) -> list:
            return []

    class _OkClient:
        def __init__(self, **kwargs) -> None:
            self.models = _OkModels()

    monkeypatch.setattr("anthropic.Anthropic", _OkClient)

    result = SystemHealthService().check_claude_api_reachability("sk-ant-test-key")
    assert result.checked is True
    assert result.reachable is True
    assert result.latency_ms is not None
