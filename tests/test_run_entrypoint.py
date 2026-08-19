"""Tests für run.py (Prompt 36/37, PyInstaller-Entry-Point; Prompt 46,
natives Fenster).

Testet nur die reine Dispatch-/Pfadlogik - die eigentlichen Subprozess-
Aufrufe (`_run_migrate_subprocess`/`_run_create_admin_subprocess`) und die
Konsoleninteraktion (`cmd_setup`s `input()`/`getpass`) werden hier NICHT
ausgeführt, sondern die jeweiligen `cmd_*`-Funktionen werden für den
Dispatch-Test durch Stubs ersetzt. Ebenso wird `_serve_with_window` (Prompt
46: echter Server-Thread + echtes WebView-Fenster) hier NICHT ausgeführt -
nur die beiden isoliert testbaren Bausteine `_wait_for_server_ready` und
`_is_webview2_runtime_available` sowie die Argument-Dispatch-Logik
(`--no-window`). Der eigentliche Bündelungs-/Installationsvorgang und das
tatsächliche Öffnen eines nativen Fensters sind nur manuell/per
PyInstaller-Build testbar (siehe Bericht am Ende der Sitzung).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

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
    monkeypatch.setattr(
        run, "cmd_serve", lambda *, open_window=True: (order.append("serve"), 0)[1]
    )

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
    monkeypatch.setattr(run, "cmd_serve", lambda *, open_window=True: 0)

    assert run.main(["serve"]) == 0


def test_main_serve_aborts_if_setup_fails(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KANZLEI_AI_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(run, "cmd_setup", lambda data_dir, *, force: 1)
    monkeypatch.setattr(
        run,
        "cmd_serve",
        lambda *, open_window=True: (_ for _ in ()).throw(
            AssertionError("Serve sollte nach fehlgeschlagenem Setup nicht aufgerufen werden")
        ),
    )

    assert run.main(["serve"]) == 1


def test_main_serve_default_opens_window(tmp_path, monkeypatch) -> None:
    """Prompt 46: ohne --no-window ist open_window=True der neue Standard."""
    monkeypatch.setenv("KANZLEI_AI_DATA_DIR", str(tmp_path))
    (tmp_path / ".env").write_text("APP_ENV=production\n", encoding="utf-8")
    recorded: list[bool] = []
    monkeypatch.setattr(
        run, "cmd_serve", lambda *, open_window=True: (recorded.append(open_window), 0)[1]
    )

    assert run.main(["serve"]) == 0
    assert recorded == [True]


def test_main_serve_bare_invocation_without_subcommand_opens_window(tmp_path, monkeypatch) -> None:
    """Auch der implizite Default (gar kein Argument) muss open_window=True
    ergeben - dort hat argparse die serve-Subparser-Attribute nie befüllt,
    das getattr-Fallback in main() muss trotzdem sicher greifen."""
    monkeypatch.setenv("KANZLEI_AI_DATA_DIR", str(tmp_path))
    (tmp_path / ".env").write_text("APP_ENV=production\n", encoding="utf-8")
    recorded: list[bool] = []
    monkeypatch.setattr(
        run, "cmd_serve", lambda *, open_window=True: (recorded.append(open_window), 0)[1]
    )

    assert run.main([]) == 0
    assert recorded == [True]


def test_main_serve_no_window_flag_disables_window(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KANZLEI_AI_DATA_DIR", str(tmp_path))
    (tmp_path / ".env").write_text("APP_ENV=production\n", encoding="utf-8")
    recorded: list[bool] = []
    monkeypatch.setattr(
        run, "cmd_serve", lambda *, open_window=True: (recorded.append(open_window), 0)[1]
    )

    assert run.main(["serve", "--no-window"]) == 0
    assert recorded == [False]


def test_wait_for_server_ready_returns_on_first_successful_check() -> None:
    calls: list[str] = []

    def fake_check(url: str) -> bool:
        calls.append(url)
        return True

    run._wait_for_server_ready(
        "http://127.0.0.1:8000/health",
        check=fake_check,
        sleep=lambda seconds: None,
        now=lambda: 0.0,
    )

    assert calls == ["http://127.0.0.1:8000/health"]


def test_wait_for_server_ready_retries_until_check_succeeds() -> None:
    results = iter([False, False, True])
    attempts: list[int] = []
    fake_clock = iter([0.0, 0.1, 0.2, 0.3])

    def fake_check(url: str) -> bool:
        attempts.append(1)
        return next(results)

    run._wait_for_server_ready(
        "http://127.0.0.1:8000/health",
        timeout=5.0,
        check=fake_check,
        sleep=lambda seconds: None,
        now=lambda: next(fake_clock),
    )

    assert sum(attempts) == 3


def test_wait_for_server_ready_raises_timeout_error_without_real_waiting() -> None:
    fake_time = {"value": 0.0}

    def fake_now() -> float:
        return fake_time["value"]

    def fake_sleep(seconds: float) -> None:
        fake_time["value"] += seconds

    with pytest.raises(TimeoutError, match="antwortete nicht|hat innerhalb von"):
        run._wait_for_server_ready(
            "http://127.0.0.1:8000/health",
            timeout=1.0,
            interval=0.25,
            check=lambda url: False,
            sleep=fake_sleep,
            now=fake_now,
        )


def test_wait_for_server_ready_includes_last_error_in_timeout_message() -> None:
    fake_time = {"value": 0.0}

    def fake_check(url: str) -> bool:
        raise ConnectionError("Verbindung verweigert")

    with pytest.raises(TimeoutError, match="Verbindung verweigert"):
        run._wait_for_server_ready(
            "http://127.0.0.1:8000/health",
            timeout=0.5,
            interval=0.1,
            check=fake_check,
            sleep=lambda seconds: fake_time.__setitem__("value", fake_time["value"] + seconds),
            now=lambda: fake_time["value"],
        )


def test_is_webview2_runtime_available_true_on_non_windows(monkeypatch) -> None:
    monkeypatch.setattr(os, "name", "posix")
    assert run._is_webview2_runtime_available() is True


def test_is_webview2_runtime_available_true_when_registry_key_found(monkeypatch) -> None:
    import winreg

    monkeypatch.setattr(os, "name", "nt")
    monkeypatch.setattr(winreg, "OpenKey", lambda hive, path: object())
    monkeypatch.setattr(winreg, "QueryValueEx", lambda key, name: ("120.0.0.0", 1))

    assert run._is_webview2_runtime_available() is True


def test_is_webview2_runtime_available_false_when_no_key_found(monkeypatch) -> None:
    import winreg

    def _raise_not_found(hive, path):
        raise OSError("Registrierungsschlüssel nicht gefunden")

    monkeypatch.setattr(os, "name", "nt")
    monkeypatch.setattr(winreg, "OpenKey", _raise_not_found)

    assert run._is_webview2_runtime_available() is False
