"""Synthetischer Testdaten-Simulator (Prompt 29).

Erzeugt realistische, vollständig fiktive Kanzlei-Fälle (Konzept-Annahme
A3: nie echte Mandantendaten) - für Demo-/Entwicklungszwecke und als
Datengrundlage für den Qualitäts-Benchmark aus Prompt 30.
"""

from app.synthetic_data.generator import SyntheticCase, SyntheticDataGenerator
from app.synthetic_data.scenarios import SCENARIOS, CaseScenario

__all__ = ["SyntheticDataGenerator", "SyntheticCase", "SCENARIOS", "CaseScenario"]
