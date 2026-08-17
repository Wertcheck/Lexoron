"""Macht `scripts/` als Package importierbar.

Nötig, damit `run.py` (Prompt 36/37, Windows-Entry-Point) die bestehende
Logik aus `scripts/create_admin.py` per Import AUFRUFEN kann, statt sie zu
duplizieren (siehe HANDOFF_PROMPT36_37_WINDOWS.md). Ändert das bisherige
Verhalten der Skripte nicht - sie bleiben weiterhin einzeln per
`python scripts/<name>.py` ausführbar.
"""
