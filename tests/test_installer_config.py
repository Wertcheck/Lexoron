"""Smoke-Test für windows/installer.iss (Schritt 3): Installation unter
%LocalAppData% ohne Admin-Rechte statt bisher {autopf} ("Program Files").
Kein echter Inno-Setup-Compile-Lauf (ISCC.exe i. d. R. nicht in der
Sandbox verfügbar) - nur eine Textprüfung der sicherheitsrelevanten
Direktiven."""

from __future__ import annotations

from pathlib import Path

_INSTALLER_PATH = Path(__file__).resolve().parent.parent / "windows" / "installer.iss"


def _read_installer() -> str:
    return _INSTALLER_PATH.read_text(encoding="utf-8")


def test_installs_under_local_app_data_not_program_files() -> None:
    content = _read_installer()
    assert "DefaultDirName={localappdata}\\KanzleiAI" in content
    assert "DefaultDirName={autopf}" not in content


def test_does_not_require_admin_privileges() -> None:
    content = _read_installer()
    assert "PrivilegesRequired=lowest" in content
    assert "PrivilegesRequired=admin" not in content
