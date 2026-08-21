"""Tests für app/local_ai/hardware_detector.py (§67).

Reine Logik-Tests mit konstruierten `HardwareProfile`-Objekten (kein echter
PowerShell-/WMI-Aufruf, damit die Suite plattformunabhängig und schnell
bleibt) - plus EIN echter Smoke-Test, der `HardwareDetector.detect()`
tatsächlich ausführt (robust genug, um auf jeder Maschine nicht
abzustürzen, siehe `test_detect_never_crashes_and_returns_a_profile`)."""

from __future__ import annotations

from app.local_ai.hardware_detector import (
    HardwareDetector,
    _parse_intel_generation,
    classify_hardware,
    has_capable_gpu,
)
from app.local_ai.hardware_schema import HardwareClass, HardwareProfile


def _profile(**overrides) -> HardwareProfile:
    defaults = {"ram_total_gb": 16.0, "cpu_vendor": "GenuineIntel", "cpu_generation": 13, "cpu_cores": 8}
    defaults.update(overrides)
    return HardwareProfile(**defaults)


# --- 1. < 16 GB RAM ---


def test_below_16gb_ram_is_always_unsupported() -> None:
    profile = _profile(ram_total_gb=8.0)
    assert classify_hardware(profile) == HardwareClass.UNSUPPORTED


def test_unknown_ram_is_unsupported() -> None:
    profile = _profile(ram_total_gb=None)
    assert classify_hardware(profile) == HardwareClass.UNSUPPORTED


# --- 2. 16 GB + Legacy-CPU (explizit: der reale i7-3720QM-Fall, §66) ---


def test_i7_3720qm_16gb_cpu_only_is_legacy_not_standard_reference() -> None:
    """Explizite Vorgabe: der alte i7-3720QM (real vermessen, §66) DARF
    NICHT als normale Referenzklasse (STANDARD) behandelt werden."""
    profile = _profile(
        ram_total_gb=15.9,  # real gemessener Wert eines physischen "16 GB"-Systems
        cpu_vendor="GenuineIntel",
        cpu_model="Intel(R) Core(TM) i7-3720QM CPU @ 2.60GHz",
        cpu_generation=3,
        cpu_cores=4,
        cpu_threads=8,
        gpu_present=True,
        gpu_vendor="Intel",
        gpu_model="Intel(R) HD Graphics 4000",
        vram_gb=2.1,
    )
    result = classify_hardware(profile)
    assert result == HardwareClass.LEGACY
    assert result != HardwareClass.STANDARD


def test_16gb_ram_reported_slightly_under_16_still_counts_as_16(monkeypatch=None) -> None:
    """Regressionsschutz fuer den real gefundenen Rundungsfehler (§67):
    ein physisch als 16 GB verkauftes System meldet ueber WMI oft nur
    ~15.9 GB - das darf NICHT automatisch zu UNSUPPORTED fuehren."""
    profile = _profile(ram_total_gb=15.9)
    assert classify_hardware(profile) != HardwareClass.UNSUPPORTED


# --- 3. 16 GB + moderne CPU ---


def test_16gb_modern_cpu_cpu_only_is_standard() -> None:
    profile = _profile(ram_total_gb=16.0, cpu_generation=13, cpu_cores=8)
    assert classify_hardware(profile) == HardwareClass.STANDARD


# --- 4. 16 GB + GPU ---


def test_16gb_with_capable_gpu_is_standard() -> None:
    profile = _profile(ram_total_gb=16.0, gpu_present=True, gpu_vendor="NVIDIA", vram_gb=8.0)
    assert classify_hardware(profile) == HardwareClass.STANDARD


def test_integrated_intel_gpu_does_not_count_as_capable() -> None:
    profile = _profile(gpu_present=True, gpu_vendor="Intel", vram_gb=2.1)
    assert has_capable_gpu(profile) is False


# --- 5/6. 32 GB CPU-only / 32 GB + GPU ---


def test_32gb_cpu_only_modern_cpu_is_performance() -> None:
    profile = _profile(ram_total_gb=32.0, cpu_generation=13, cpu_cores=8)
    assert classify_hardware(profile) == HardwareClass.PERFORMANCE


def test_32gb_with_capable_gpu_is_performance() -> None:
    profile = _profile(ram_total_gb=32.0, gpu_present=True, gpu_vendor="NVIDIA", vram_gb=10.0)
    assert classify_hardware(profile) == HardwareClass.PERFORMANCE


# --- 7. 64 GB + starke GPU ---


def test_64gb_with_strong_gpu_is_workstation() -> None:
    profile = _profile(ram_total_gb=64.0, gpu_present=True, gpu_vendor="NVIDIA", vram_gb=24.0)
    assert classify_hardware(profile) == HardwareClass.WORKSTATION


def test_64gb_with_modest_gpu_is_not_automatically_workstation() -> None:
    """64 GB allein reicht nicht - siehe Vorgabe: RAM allein darf nicht
    die einzige Entscheidungsgrundlage sein."""
    profile = _profile(ram_total_gb=64.0, gpu_present=True, gpu_vendor="NVIDIA", vram_gb=6.0)
    assert classify_hardware(profile) != HardwareClass.WORKSTATION


# --- 8/9. unbekannte GPU / unbekanntes VRAM ---


def test_unknown_gpu_vendor_is_not_treated_as_capable() -> None:
    profile = _profile(gpu_present=True, gpu_vendor=None, vram_gb=8.0)
    assert has_capable_gpu(profile) is False


def test_unknown_vram_is_not_treated_as_capable() -> None:
    profile = _profile(gpu_present=True, gpu_vendor="NVIDIA", vram_gb=None)
    assert has_capable_gpu(profile) is False


# --- 10. unbekannte CPU-Generation ---


def test_unknown_cpu_generation_does_not_force_legacy() -> None:
    """Unbekannte Generation (z. B. eine nicht erkannte AMD-CPU) darf NICHT
    automatisch als "legacy" gewertet werden - das waere ein
    unbegruendetes Urteil ueber moeglicherweise moderne Hardware."""
    profile = _profile(cpu_vendor="AuthenticAMD", cpu_generation=None, cpu_cores=8)
    assert classify_hardware(profile) == HardwareClass.STANDARD


def test_unrecognized_cpu_model_string_yields_none_generation() -> None:
    assert _parse_intel_generation("AMD Ryzen 7 5800X 8-Core Processor") is None


def test_intel_4_digit_generation_parsed_correctly() -> None:
    assert _parse_intel_generation("Intel(R) Core(TM) i7-3720QM CPU @ 2.60GHz") == 3


def test_intel_5_digit_generation_parsed_correctly() -> None:
    assert _parse_intel_generation("13th Gen Intel(R) Core(TM) i7-13700K") == 13


# --- 11. zu wenig Speicher (Disk) ---


def test_free_disk_gb_field_present_and_not_fabricated_when_unknown() -> None:
    profile = HardwareProfile()
    assert profile.free_disk_gb is None  # kein erfundener Default


# --- niedrige Kernzahl -> ebenfalls legacy, unabhaengig von der Generation ---


def test_very_low_core_count_is_legacy_even_with_unknown_generation() -> None:
    profile = _profile(cpu_vendor="AuthenticAMD", cpu_generation=None, cpu_cores=2)
    assert classify_hardware(profile) == HardwareClass.LEGACY


# --- Robustheit: echte Erkennung darf nie abstuerzen ---


def test_detect_never_crashes_and_returns_a_profile() -> None:
    """Echter Smoke-Test (kein Mock): `detect()` muss auf JEDER Maschine
    ein `HardwareProfile` zurueckgeben, selbst wenn einzelne Werte nicht
    ermittelbar sind - siehe Vorgabe "Installation nicht unnoetig
    abbrechen"."""
    profile = HardwareDetector().detect()
    assert isinstance(profile, HardwareProfile)
    assert isinstance(profile.hardware_class, HardwareClass)
    assert isinstance(profile.detection_warnings, list)
