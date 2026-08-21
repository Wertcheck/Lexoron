"""HardwareProfile – strukturierte Beschreibung der lokalen Hardware (§67).

`HardwareClass` klassifiziert NICHT nur nach RAM (Vorgabe, wörtlich: "Die
Klassifikation darf NICHT nur nach RAM erfolgen") - siehe
`hardware_detector.py::classify_hardware` für die eigentliche Logik. Jedes
Feld ist bewusst `| None`, wenn es nicht ermittelt werden konnte - ein
fehlender Wert wird NIE durch einen erfundenen Standardwert ersetzt
(`detection_warnings` hält fest, was nicht ermittelbar war)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class HardwareClass(str, Enum):
    #: < 16 GB RAM - lokale KI wird nicht als regulaer unterstuetzte
    #: Installation angeboten (Produkt-Mindestanforderung, §67).
    UNSUPPORTED = "unsupported"
    #: >= 16 GB RAM, aber alte/schwache CPU ohne brauchbare GPU-
    #: Beschleunigung - "unterstuetzt, aber nicht empfohlen" fuer
    #: interaktive Nutzung (siehe real vermessener i7-3720QM-Fall, §66).
    LEGACY = "legacy"
    #: >= 16 GB RAM, moderne CPU (CPU-only) oder GPU mit bescheidenem VRAM -
    #: typischer heutiger Kanzlei-Buero-PC.
    STANDARD = "standard"
    #: >= 32 GB RAM MIT geeigneter GPU (nennenswertes VRAM) - spuerbar mehr
    #: lokale Leistungsreserve.
    PERFORMANCE = "performance"
    #: >= 64 GB RAM MIT starker GPU - deutlich ueberdurchschnittliche
    #: Ausstattung, kein realistischer Standard-Kanzlei-PC.
    WORKSTATION = "workstation"


@dataclass
class HardwareProfile:
    os: str | None = None
    architecture: str | None = None
    cpu_model: str | None = None
    cpu_vendor: str | None = None
    # Nur fuer Intel-Core-Namensschemata heuristisch ermittelt (z. B.
    # "i7-3720QM" -> 3). None bei anderen Herstellern/nicht erkennbarem
    # Namensschema - bewusst KEINE geratene Generation.
    cpu_generation: int | None = None
    cpu_cores: int | None = None
    cpu_threads: int | None = None
    ram_total_gb: float | None = None
    ram_available_gb: float | None = None
    gpu_present: bool = False
    gpu_vendor: str | None = None
    gpu_model: str | None = None
    # None, wenn keine GPU vorhanden ODER VRAM nicht ermittelbar war -
    # bewusst nicht mit 0 verwechselbar.
    vram_gb: float | None = None
    free_disk_gb: float | None = None
    hardware_class: HardwareClass = HardwareClass.UNSUPPORTED
    # Jeder Eintrag beschreibt, WAS nicht ermittelt werden konnte und
    # WARUM (z. B. "GPU-Erkennung fehlgeschlagen: PowerShell nicht
    # verfuegbar") - niemals eine stille Annahme.
    detection_warnings: list[str] = field(default_factory=list)
