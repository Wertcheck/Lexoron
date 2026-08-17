"""Setup-/Konfigurationsassistent für die Windows-Installation (Prompt 37).

Trennt bewusst in drei kleine, unabhängig testbare Bausteine:
- `paths`: wo das persistente Datenverzeichnis liegt (siehe ARCHITECTURE.md
  für die Begründung von %PROGRAMDATA%).
- `env_writer`: reine Textgenerierung/-schreiblogik für die erzeugte
  Produktions-`.env`-Datei, ohne Seiteneffekte außer dem einen Dateischreiben.
- `wizard`: orchestriert beides plus die (injizierten, damit testbaren)
  Aufrufe von Datenbankmigration und `scripts/create_admin.py`.

Die eigentliche Interaktion mit dem Nutzer (Konsole, `input()`) lebt bewusst
NICHT hier, sondern im dünnen `run.py`-Entry-Point - dieses Paket bleibt
vollständig ohne Konsolen-I/O und damit ohne Mocking von `input()` testbar.
"""

from .env_writer import build_env_content, write_env_file
from .paths import resolve_data_dir
from .wizard import WizardError, run_setup_wizard

__all__ = [
    "build_env_content",
    "write_env_file",
    "resolve_data_dir",
    "run_setup_wizard",
    "WizardError",
]
