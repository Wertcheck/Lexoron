# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller-Spec für die Windows-Installation (Prompt 36; natives
Fenster Prompt 46).

Erzeugt einen "onedir"-Build (bewusst KEIN "onefile"): onefile extrahiert
sich bei JEDEM Start neu in ein temporäres Verzeichnis (spürbar langsamerer
Start, zusätzlicher Schreibzugriff bei jedem Programmstart, schwerer
nachvollziehbare Pfadprobleme). "onedir" passt außerdem direkt zu Inno Setup
(siehe windows/installer.iss), das den erzeugten Ordner 1:1 unter
"Program Files" installiert.

`console=True` bleibt bewusst auch nach Prompt 46 gesetzt: der Setup-
Assistent (Prompt 37, app/setup/, ausgelöst über run.py "setup"/erster
"serve"-Aufruf) fragt weiterhin interaktiv über die Konsole (`input()`/
`getpass`) nach der Admin-E-Mail-Adresse, BEVOR das native Fenster
(pywebview) überhaupt aufgebaut wird - ohne Konsole gäbe es dafür keine
Eingabemöglichkeit. Der PyInstaller-`console`-Modus ist eine feste
Build-Zeit-Einstellung für die gesamte .exe, nicht pro Aufruf umschaltbar -
ein Umschalten (Konsole nur beim allerersten Start, danach rein
fensterbasiert) wäre über einen separaten, versteckten Zweit-Prozess lösbar,
aber ein deutlich größerer Schritt als hier gerechtfertigt (siehe
ARCHITECTURE.md, offene Punkte). Nach dem allerersten Setup bleibt die
Konsole also weiterhin sichtbar neben dem nativen Fenster - eine bewusst in
Kauf genommene, kleinere kosmetische Einschränkung.

Aufruf (aus dem Projekt-Root, mit aktivierter venv,
`pip install -e .[build]` vorher ausgeführt):

    pyinstaller windows/kanzlei_ai.spec --distpath dist --workpath build

Ergebnis: dist/kanzlei_ai/kanzlei_ai.exe + alle Abhängigkeiten im selben
Ordner - genau der Ordner, den windows/installer.iss anschließend
verpackt.
"""

from pathlib import Path

PROJECT_ROOT = Path(SPECPATH).resolve().parent  # noqa: F821 (SPECPATH von PyInstaller injiziert)

a = Analysis(  # noqa: F821 (von PyInstaller zur Laufzeit des Specs injiziert)
    [str(PROJECT_ROOT / "run.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[
        # Migrationen + alembic.ini: von "run.py migrate" zur Laufzeit
        # gebraucht (alembic liest Migrationsskripte als Dateien vom
        # Datenträger, nicht per Python-Import - PyInstallers
        # Import-Analyse sieht sie daher nicht automatisch).
        (str(PROJECT_ROOT / "migrations"), "migrations"),
        (str(PROJECT_ROOT / "alembic.ini"), "."),
        # Templates/statische Assets: siehe app/web/template_paths.py -
        # müssen unter demselben relativen Pfad liegen, den die dortigen
        # Path(__file__)-Berechnungen erwarten.
        (str(PROJECT_ROOT / "app" / "web" / "templates"), "app/web/templates"),
        (str(PROJECT_ROOT / "app" / "web" / "static"), "app/web/static"),
    ],
    hiddenimports=[
        # run.py importiert dies erst zur Laufzeit (lazy import in
        # cmd_create_admin) - PyInstallers statische Analyse verfolgt
        # verschachtelte/späte Imports nicht immer zuverlässig.
        "scripts.create_admin",
        "migrations.env",
        # SQLAlchemy laedt Dialekte z. T. dynamisch nach.
        "sqlalchemy.dialects.sqlite",
        # pywebview (Prompt 46): waehlt sein Windows-Backend
        # (webview.platforms.winforms, das intern wiederum EdgeChromium
        # ODER als Fallback das veraltete MSHTML importiert) erst zur
        # Laufzeit innerhalb eines try/except - hier explizit als
        # hiddenimport ergaenzt, auch wenn PyInstallers AST-Analyse
        # bedingte Imports normalerweise bereits findet (Vorsichtsmassnahme,
        # analog zu "migrations.env" oben). Die dafuer noetigen DLLs
        # (WebView2-Loader, clr_loader/.NET-Interop) sammelt bereits
        # "pyinstaller-hooks-contrib" automatisch ein (hook-webview.py,
        # hook-clr_loader.py, seit Version 2026.6 im Projekt via
        # PyInstaller selbst mitinstalliert) - hier daher KEINE eigene
        # collect_dynamic_libs()-Handhabung noetig.
        "webview.platforms.winforms",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="kanzlei_ai",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="kanzlei_ai",
)
