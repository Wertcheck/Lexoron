"""Regressionstest für app/web/template_paths.py (Prompt 36).

Bei der Umsetzung des Windows-Installers entdeckt: alle acht Verwendungs-
stellen von `Jinja2Templates`/`StaticFiles` nutzten vorher einen relativen
Pfad ("app/web/templates"/"app/web/static"), aufgelöst gegen das
Arbeitsverzeichnis des Prozesses. Der Windows-Entry-Point (`run.py`)
wechselt das Arbeitsverzeichnis beim Start bewusst in das persistente
Datenverzeichnis (siehe app/setup/paths.py) - mit dem alten relativen Pfad
wäre das gesamte Dashboard (jede Seite, jedes statische Asset) dort
funktionslos gewesen. Dieser Test hält die Behebung dauerhaft fest.
"""

from pathlib import Path

from app.web.template_paths import STATIC_DIR, TEMPLATES_DIR


def test_templates_and_static_dirs_exist_and_are_absolute() -> None:
    assert Path(TEMPLATES_DIR).is_absolute()
    assert Path(TEMPLATES_DIR).is_dir()
    assert Path(STATIC_DIR).is_absolute()
    assert Path(STATIC_DIR).is_dir()


def test_paths_do_not_depend_on_current_working_directory(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert Path(TEMPLATES_DIR).is_dir()
    assert Path(STATIC_DIR).is_dir()
