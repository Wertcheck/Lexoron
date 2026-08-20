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


def test_registers_app_identity_for_apps_and_features() -> None:
    """Diese vier Werte sind Voraussetzung dafür, dass Windows nach der
    Installation überhaupt einen sauberen, eindeutigen Eintrag unter
    "Apps & Features"/"Programme und Funktionen" anlegt (Inno Setup
    generiert Uninstaller + Registrierung daraus automatisch - kein
    zusätzliches Skript nötig)."""
    content = _read_installer()
    assert "AppId={{9F4B9E7A-2B1E-4C77-9C7C-3D9B5E5B0B21}}" in content
    assert 'AppName={#MyAppName}' in content
    assert 'AppVersion={#MyAppVersion}' in content
    assert 'AppPublisher={#MyAppPublisher}' in content


def test_uninstall_entry_shows_the_real_app_icon() -> None:
    content = _read_installer()
    assert "UninstallDisplayIcon={app}\\{#MyAppExeName}" in content


def test_creates_start_menu_shortcut() -> None:
    content = _read_installer()
    assert 'Name: "{group}\\{#MyAppName}"; Filename: "{app}\\{#MyAppExeName}"' in content
    # Eigener Deinstallations-Eintrag im Startmenü zusätzlich zum
    # automatischen "Apps & Features"-Eintrag.
    assert '{uninstallexe}' in content


def test_creates_desktop_shortcut_checked_by_default() -> None:
    content = _read_installer()
    assert (
        'Name: "{autodesktop}\\{#MyAppName}"; Filename: "{app}\\{#MyAppExeName}"' in content
    )
    # Der Task existiert weiterhin (abwählbar), ist aber seit dieser
    # Anfrage NICHT mehr per "unchecked" abgewählt vorbelegt.
    assert 'Name: "desktopicon"' in content
    assert "Flags: unchecked" not in content


def test_output_filename_matches_requested_exe_name() -> None:
    content = _read_installer()
    assert "OutputBaseFilename=KanzleiAI_Setup" in content
