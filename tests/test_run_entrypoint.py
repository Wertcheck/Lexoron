"""Tests für run.py (Prompt 36/37, PyInstaller-Entry-Point).

Testet nur die reine Dispatch-/Pfadlogik - die eigentlichen Subprozess-
Aufrufe (`_run_migrate_subprocess`/`_run_create_admin_subprocess`) und die
Konsoleninteraktion (`cmd_setup`s `input()`/`getpass`) werden hier NICHT
ausgeführt, sondern die jeweiligen `cmd_*`-Funktionen werden für den
Dispatch-Test durch Stubs ersetzt. Der eigentliche Bündelungs-/
Installationsvorgang selbst ist nur manuell/per PyInstaller-Build testbar
(siehe Bericht am Ende der Sitzung).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import run


def test_bundle_base_dir_in_dev_mode_is_repo_root(monkeypatch) -> None:
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    assert run._bundle_base_dir() == Path(run.__file__).resolve().parent


def test_self_command_in_dev_mode_uses_python_and_script_path(monkeypatch) -> None:
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    command = run._self_command("migrate")
    assert command == [sys.executable, str(Path(run.__file__).resolve()), "migrate"]


def test_self_command_when_frozen_uses_only_executable(monkeypatch) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\Program Files\KanzleiAI\kanzlei_ai.exe")
    command = run._self_command("create-admin")
    assert command == [r"C:\Program Files\KanzleiAI\kanzlei_ai.exe", "create-admin"]


def test_main_changes_into_resolved_data_dir(tmp_path, monkeypatch) -> None:
    original_cwd = Path.cwd()
    monkeypatch.setenv("KANZLEI_AI_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(run, "cmd_migrate", lambda: 0)

    try:
        exit_code = run.main(["migrate"])
        assert exit_code == 0
        assert Path.cwd().resolve() == tmp_path.resolve()
    finally:
        os.chdir(original_cwd)


def test_main_dispatches_migrate(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KANZLEI_AI_DATA_DIR", str(tmp_path))
    calls: list[str] = []
    monkeypatch.setattr(run, "cmd_migrate", lambda: (calls.append("migrate"), 0)[1])

    assert run.main(["migrate"]) == 0
    assert calls == ["migrate"]


def test_main_dispatches_create_admin(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KANZLEI_AI_DATA_DIR", str(tmp_path))
    calls: list[str] = []
    monkeypatch.setattr(run, "cmd_create_admin", lambda: (calls.append("create-admin"), 0)[1])

    assert run.main(["create-admin"]) == 0
    assert calls == ["create-admin"]


def test_main_dispatches_setup_with_force_flag(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KANZLEI_AI_DATA_DIR", str(tmp_path))
    recorded: list[tuple[Path, bool]] = []

    def fake_cmd_setup(data_dir: Path, *, force: bool) -> int:
        recorded.append((data_dir, force))
        return 0

    monkeypatch.setattr(run, "cmd_setup", fake_cmd_setup)

    assert run.main(["setup", "--force"]) == 0
    assert recorded == [(tmp_path, True)]


def test_main_serve_without_env_runs_setup_first(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KANZLEI_AI_DATA_DIR", str(tmp_path))
    order: list[str] = []
    monkeypatch.setattr(
        run, "cmd_setup", lambda data_dir, *, force: (order.append("setup"), 0)[1]
    )
    monkeypatch.setattr(run, "cmd_serve", lambda: (order.append("serve"), 0)[1])

    assert run.main([]) == 0
    assert order == ["setup", "serve"]


def test_main_serve_skips_setup_when_env_already_exists(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KANZLEI_AI_DATA_DIR", str(tmp_path))
    (tmp_path / ".env").write_text("APP_ENV=production\n", encoding="utf-8")

    monkeypatch.setattr(
        run,
        "cmd_setup",
        lambda data_dir, *, force: (_ for _ in ()).throw(
            AssertionError("Setup sollte bei bestehender .env nicht aufgerufen werden")
        ),
    )
    monkeypatch.setattr(run, "cmd_serve", lambda: 0)

    assert run.main(["serve"]) == 0


def test_main_serve_aborts_if_setup_fails(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KANZLEI_AI_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(run, "cmd_setup", lambda data_dir, *, force: 1)
    monkeypatch.setattr(
        run,
        "cmd_serve",
        lambda: (_ for _ in ()).throw(
            AssertionError("Serve sollte nach fehlgeschlagenem Setup nicht aufgerufen werden")
        ),
    )

    assert run.main(["serve"]) == 1
