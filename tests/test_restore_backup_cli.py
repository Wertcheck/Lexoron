"""Tests für scripts/restore_backup.py (Schritt 3, Teil 2) - reine
CLI-/Bestätigungslogik, RestoreService selbst ist in
tests/test_restore_service.py abgedeckt."""

from __future__ import annotations

import pytest

from scripts import restore_backup


def test_declining_confirmation_aborts_without_calling_service(
    monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    monkeypatch.setattr("builtins.input", lambda _: "nein")

    def _must_not_be_called(*args, **kwargs):
        raise AssertionError("RestoreService haette nicht aufgerufen werden duerfen")

    monkeypatch.setattr(restore_backup, "RestoreService", _must_not_be_called)

    exit_code = restore_backup.main(["--archive", "backup.zip"])

    assert exit_code == 1


def test_yes_flag_skips_interactive_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fail_on_input(_):
        raise AssertionError("input() haette bei --yes nicht aufgerufen werden duerfen")

    monkeypatch.setattr("builtins.input", _fail_on_input)

    calls: list[str] = []

    class _FakeResult:
        pre_restore_database_backup = None
        intake_files_restored = 0
        mail_attachment_files_restored = 0

    class _FakeService:
        def __init__(self, **kwargs) -> None:
            calls.append("constructed")

        def restore_from_backup(self, archive, *, confirm: bool):
            calls.append(f"restore(confirm={confirm})")
            return _FakeResult()

    monkeypatch.setattr(restore_backup, "RestoreService", _FakeService)

    exit_code = restore_backup.main(["--archive", "backup.zip", "--yes"])

    assert exit_code == 0
    assert calls == ["constructed", "restore(confirm=True)"]


def test_confirming_with_ja_proceeds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("builtins.input", lambda _: "JA")

    calls: list[str] = []

    class _FakeResult:
        pre_restore_database_backup = None
        intake_files_restored = 2
        mail_attachment_files_restored = 1

    class _FakeService:
        def __init__(self, **kwargs) -> None:
            pass

        def restore_from_backup(self, archive, *, confirm: bool):
            calls.append(f"restore(confirm={confirm})")
            return _FakeResult()

    monkeypatch.setattr(restore_backup, "RestoreService", _FakeService)

    exit_code = restore_backup.main(["--archive", "backup.zip"])

    assert exit_code == 0
    assert calls == ["restore(confirm=True)"]


def test_restore_error_from_service_returns_nonzero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("builtins.input", lambda _: "JA")

    class _FakeService:
        def __init__(self, **kwargs) -> None:
            pass

        def restore_from_backup(self, archive, *, confirm: bool):
            raise restore_backup.RestoreError("Archiv ungueltig")

    monkeypatch.setattr(restore_backup, "RestoreService", _FakeService)

    exit_code = restore_backup.main(["--archive", "backup.zip"])

    assert exit_code == 1
