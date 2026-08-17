# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller-Spec für die Windows-Installation (Prompt 36).

Erzeugt einen "onedir"-Build (bewusst KEIN "onefile"): onefile extrahiert
sich bei JEDEM Start neu in ein temporäres Verzeichnis (spürbar langsamerer
Start, zusätzlicher Schreibzugriff bei jedem Programmstart, schwerer
nachvollziehbare Pfadprobleme). "onedir" passt außerdem direkt zu Inno Setup
(siehe windows/installer.iss), das den erzeugten Ordner 1:1 unter
"Program Files" installiert.

`console=True` ist bewusst gesetzt: der Setup-Assistent (Prompt 37,
app/setup/, ausgelöst über run.py "setup"/erster "serve"-Aufruf) fragt
interaktiv über die Konsole (`input()`/`getpass`) nach der Admin-E-Mail-
Adresse - eine grafische Oberfläche existiert im gesamten Projekt bewusst
nicht (das Dashboard selbst läuft im Browser). Die Anwendung läuft damit
als Konsolenprozess im Vordergrund, NICHT als registrierter Windows-Dienst -
letzteres wäre ein deutlich größerer Schritt (Dienstkonto, Autostart,
Absturz-Neustart) und war nicht Teil dieses Prompts, siehe ARCHITECTURE.md.

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
