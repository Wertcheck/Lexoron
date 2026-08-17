"""Auflösung des persistenten Datenverzeichnisses (Prompt 36/37).

Entscheidung (siehe ARCHITECTURE.md, Abschnitt zum Windows-Installer):
Konfiguration (.env), Datenbank und Dokumentenspeicher liegen NICHT im
Installationsverzeichnis (typischerweise "Program Files", nur für
Administratoren beschreibbar und kein sinnvoller Ort für sich ständig
ändernde Mandantendaten) und NICHT in einem vom Nutzerprofil abhängigen,
potenziell durch OneDrive-Ordnerschutz ("Bekannte Ordner sichern") überwachten
Verzeichnis wie Dokumente/Desktop/Bilder. Stattdessen: `%PROGRAMDATA%`
(Standard-Windows-Konvention für maschinenweite, nicht profilgebundene
Anwendungsdaten, per Voreinstellung von normalen Nutzerkonten beschreibbar,
NICHT Teil des OneDrive-"Bekannte Ordner"-Satzes).
"""

from __future__ import annotations

import os
from pathlib import Path

#: Überschreibt die automatische Ermittlung vollständig - nützlich für Tests
#: und für einen künftigen Portable-/Entwicklungsmodus.
_OVERRIDE_ENV_VAR = "KANZLEI_AI_DATA_DIR"

#: Name des Unterverzeichnisses unterhalb von %PROGRAMDATA%.
_APP_DIR_NAME = "KanzleiAI"


def resolve_data_dir(*, is_windows: bool | None = None) -> Path:
    """Liefert das persistente Datenverzeichnis für diese Installation.

    Reihenfolge: explizite Überschreibung (`KANZLEI_AI_DATA_DIR`) > Windows-
    Standardpfad (`%PROGRAMDATA%\\KanzleiAI`) > Fallback für Nicht-Windows-
    Entwicklungsumgebungen (`~/.kanzlei_ai`) - das Projekt zielt ausschließlich
    auf Windows als Installationsplattform (siehe CLAUDE.md/HANDOFF), der
    Fallback existiert nur, damit dieses Modul auch außerhalb von Windows
    importierbar/testbar bleibt.

    `is_windows` ist bewusst injizierbar (statt die Entscheidung nur intern
    an `os.name` festzumachen): `os.name` global per `monkeypatch.setattr`
    umzubiegen bricht auf Python 3.13 nachweislich `Path.home()`, das seinerseits
    intern auf `os.name` prüft (siehe git-history dieser Datei/zugehöriger
    Test) - ein injizierbarer Parameter macht beide Zweige testbar, ohne den
    tatsächlichen Plattform-Zustand zu verändern.
    """
    override = os.environ.get(_OVERRIDE_ENV_VAR)
    if override:
        return Path(override)

    if is_windows is None:
        is_windows = os.name == "nt"

    if is_windows:
        program_data = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
        return Path(program_data) / _APP_DIR_NAME

    return Path.home() / ".kanzlei_ai"
