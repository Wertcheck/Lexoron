"""HardwareDetector – ermittelt die reale lokale Hardware (§67, Windows-
Fokus, siehe CLAUDE.md/ARCHITECTURE.md fuer den Windows-Zielrechner).

JEDE Einzel-Erkennung ist in ein eigenes `try/except` gekapselt: schlaegt
ein Schritt fehl (z. B. PowerShell nicht verfuegbar, WMI-Abfrage
verweigert), bleibt NUR das betroffene Feld `None` und ein Eintrag landet
in `detection_warnings` - die Erkennung als Ganzes bricht nie ab und
erfindet nie einen Ersatzwert (Vorgabe, woertlich: "Keine erfundenen
Hardwarewerte").

Real auf einem Intel Core i7-3720QM (3. Generation, 4 Kerne/8 Threads,
16 GB RAM, Intel HD Graphics 4000, Windows 10 Pro) verifiziert - siehe
ARCHITECTURE.md §67 fuer das Ergebnis dieser konkreten Maschine."""

from __future__ import annotations

import json
import platform
import re
import shutil
import subprocess

from app.local_ai.hardware_schema import HardwareClass, HardwareProfile

# Nur Namen bekannter dedizierter GPU-Hersteller - eine im System
# eingebaute Intel-/AMD-Chipsatzgrafik ("integrated") beschleunigt lokale
# LLM-Inferenz in der Praxis nicht nennenswert (siehe has_capable_gpu) -
# wird trotzdem korrekt als "vorhanden" erfasst (gpu_present=True), nur
# nicht automatisch als leistungsfaehig gewertet.
_DEDICATED_GPU_VENDOR_KEYWORDS = (
    ("NVIDIA", "NVIDIA"),
    ("AMD", "AMD"),
    ("Radeon", "AMD"),
    ("Intel", "Intel"),
)

# Intel-Core-Namensschema ("i7-3720QM", "i9-13900K", "i5-8250U") - die
# ersten 1-2 Ziffern nach dem Bindestrich sind die Generation. NUR fuer
# dieses eine, gut dokumentierte Namensschema - andere Hersteller (AMD
# Ryzen, Apple Silicon) haben kein vergleichbar simples Muster und werden
# bewusst NICHT geraten (cpu_generation bleibt None).
_INTEL_CORE_GENERATION_PATTERN = re.compile(r"\bi[3579]-(\d{4,5})[A-Z]*\b")


def _parse_intel_generation(cpu_model: str) -> int | None:
    match = _INTEL_CORE_GENERATION_PATTERN.search(cpu_model)
    if not match:
        return None
    digits = match.group(1)
    # 4-stellig (z. B. "3720") -> 1 Generationsziffer, 5-stellig
    # (z. B. "13900") -> 2 Generationsziffern (Intel-Namenskonvention ab
    # der 10. Generation).
    generation_digits = 1 if len(digits) == 4 else 2
    try:
        return int(digits[:generation_digits])
    except ValueError:
        return None


def _run_powershell(command: str, *, timeout: float = 10.0) -> str | None:
    """Fuehrt einen PowerShell-Befehl aus, gibt stdout zurueck oder `None`
    bei jedem Fehler (fehlendes powershell.exe, Timeout, Exit-Code != 0) -
    wirft NIE, damit ein einzelner fehlgeschlagener Erkennungsschritt die
    gesamte Hardware-Erkennung nicht abbricht."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except Exception:  # noqa: BLE001 - jeder Fehler bedeutet "nicht ermittelbar"
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return result.stdout.strip()


class HardwareDetector:
    def detect(self) -> HardwareProfile:
        profile = HardwareProfile()

        self._detect_os(profile)
        self._detect_cpu(profile)
        self._detect_ram(profile)
        self._detect_gpu(profile)
        self._detect_disk(profile)

        profile.hardware_class = classify_hardware(profile)
        return profile

    def _detect_os(self, profile: HardwareProfile) -> None:
        try:
            profile.os = platform.platform()
            profile.architecture = platform.machine()
        except Exception as exc:  # noqa: BLE001
            profile.detection_warnings.append(
                f"Betriebssystem-/Architektur-Erkennung fehlgeschlagen: {type(exc).__name__}"
            )

    def _detect_cpu(self, profile: HardwareProfile) -> None:
        output = _run_powershell(
            "Get-CimInstance Win32_Processor | Select-Object -First 1 "
            "Name,Manufacturer,NumberOfCores,NumberOfLogicalProcessors | ConvertTo-Json"
        )
        if output is None:
            profile.detection_warnings.append(
                "CPU-Erkennung fehlgeschlagen: Win32_Processor ueber PowerShell "
                "nicht abrufbar"
            )
            return
        try:
            data = json.loads(output)
        except ValueError:
            profile.detection_warnings.append(
                "CPU-Erkennung fehlgeschlagen: Antwort nicht als JSON lesbar"
            )
            return

        cpu_model = data.get("Name")
        if isinstance(cpu_model, str):
            profile.cpu_model = cpu_model.strip()
            profile.cpu_generation = _parse_intel_generation(profile.cpu_model)
            if profile.cpu_generation is None:
                profile.detection_warnings.append(
                    "CPU-Generation nicht ermittelbar (kein bekanntes Intel-Core-"
                    "Namensschema oder anderer Hersteller)"
                )
        else:
            profile.detection_warnings.append("CPU-Modellname nicht ermittelbar")

        profile.cpu_vendor = data.get("Manufacturer")
        cores = data.get("NumberOfCores")
        threads = data.get("NumberOfLogicalProcessors")
        profile.cpu_cores = int(cores) if isinstance(cores, (int, float)) else None
        profile.cpu_threads = int(threads) if isinstance(threads, (int, float)) else None

    def _detect_ram(self, profile: HardwareProfile) -> None:
        output = _run_powershell(
            "(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory"
        )
        if output is not None:
            try:
                profile.ram_total_gb = round(int(output.strip()) / (1024**3), 1)
            except ValueError:
                profile.detection_warnings.append(
                    "RAM-Gesamtgroesse nicht ermittelbar: unerwartetes Format"
                )
        else:
            profile.detection_warnings.append(
                "RAM-Gesamtgroesse nicht ermittelbar: WMI-Abfrage fehlgeschlagen"
            )

        available_output = _run_powershell(
            "(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory"
        )
        if available_output is not None:
            try:
                # FreePhysicalMemory ist in KB angegeben (WMI-Konvention),
                # NICHT in Bytes wie TotalPhysicalMemory.
                profile.ram_available_gb = round(int(available_output.strip()) / (1024**2), 1)
            except ValueError:
                profile.detection_warnings.append(
                    "Verfuegbarer RAM nicht ermittelbar: unerwartetes Format"
                )
        else:
            profile.detection_warnings.append(
                "Verfuegbarer RAM nicht ermittelbar: WMI-Abfrage fehlgeschlagen"
            )

    def _detect_gpu(self, profile: HardwareProfile) -> None:
        output = _run_powershell(
            "Get-CimInstance Win32_VideoController | Select-Object Name,AdapterRAM | ConvertTo-Json"
        )
        if output is None:
            profile.detection_warnings.append(
                "GPU-Erkennung fehlgeschlagen: Win32_VideoController ueber "
                "PowerShell nicht abrufbar"
            )
            return
        try:
            data = json.loads(output)
        except ValueError:
            profile.detection_warnings.append(
                "GPU-Erkennung fehlgeschlagen: Antwort nicht als JSON lesbar"
            )
            return

        entries = data if isinstance(data, list) else [data]
        entries = [e for e in entries if isinstance(e, dict) and e.get("Name")]
        if not entries:
            profile.detection_warnings.append("Keine GPU ueber WMI gemeldet")
            return

        # Bei mehreren Grafikkarten (z. B. Intel-iGPU + dedizierte GPU)
        # bevorzugt die erste mit einem bekannten dedizierten Hersteller-
        # Namen - sonst die erste gemeldete (typischerweise die iGPU).
        chosen = entries[0]
        for entry in entries:
            name = entry.get("Name", "")
            if any(
                keyword in name and vendor != "Intel"
                for keyword, vendor in _DEDICATED_GPU_VENDOR_KEYWORDS
            ):
                chosen = entry
                break

        name = chosen.get("Name")
        profile.gpu_present = True
        profile.gpu_model = name
        for keyword, vendor in _DEDICATED_GPU_VENDOR_KEYWORDS:
            if keyword in name:
                profile.gpu_vendor = vendor
                break
        else:
            profile.detection_warnings.append(
                f"GPU-Hersteller aus Namen nicht erkennbar: {name!r}"
            )

        adapter_ram = chosen.get("AdapterRAM")
        if isinstance(adapter_ram, (int, float)) and adapter_ram > 0:
            profile.vram_gb = round(adapter_ram / (1024**3), 1)
            # Bekannte WMI-Einschraenkung, ehrlich vermerkt statt
            # stillschweigend als praezise Angabe behandelt: AdapterRAM
            # ist fuer moderne dediziertere Karten teils falsch/gekappt
            # (32-Bit-Feld) - siehe detection_warnings.
            profile.detection_warnings.append(
                "VRAM-Wert stammt aus WMI AdapterRAM - bei manchen modernen GPUs "
                "bekanntermassen ungenau/gekappt, nicht als praezise Angabe zu werten"
            )
        else:
            profile.detection_warnings.append(
                f"VRAM fuer '{name}' nicht ermittelbar (kein/kein plausibler "
                "AdapterRAM-Wert)"
            )

    def _detect_disk(self, profile: HardwareProfile) -> None:
        output = _run_powershell(
            "(Get-CimInstance Win32_LogicalDisk -Filter \"DeviceID='C:'\").FreeSpace"
        )
        if output is None:
            profile.detection_warnings.append(
                "Freier Speicherplatz nicht ermittelbar: WMI-Abfrage fehlgeschlagen"
            )
            return
        try:
            profile.free_disk_gb = round(int(output.strip()) / (1024**3), 1)
        except ValueError:
            profile.detection_warnings.append(
                "Freier Speicherplatz nicht ermittelbar: unerwartetes Format"
            )


# --- Hardwareklassen-Klassifikation ------------------------------------

# Nennenswerte VRAM-Schwelle, ab der eine GPU ueberhaupt als
# "brauchbar beschleunigend" fuer lokale LLM-Inferenz gilt - eine
# integrierte Buero-GPU (z. B. Intel HD/UHD Graphics) liegt bewusst
# darunter (kein separates VRAM, nutzt geteilten RAM).
_MIN_CAPABLE_GPU_VRAM_GB = 6.0
# Unterhalb dieser Intel-Core-Generation gilt eine CPU-only-Maschine als
# "legacy" (siehe real vermessener i7-3720QM = Generation 3, §66/§67) -
# bewusst konservativ: 3. Generation (2012) ist über zehn Jahre alt.
_LEGACY_INTEL_GENERATION_THRESHOLD = 5
_LEGACY_MIN_CORES_THRESHOLD = 4


def has_capable_gpu(profile: HardwareProfile) -> bool:
    if not profile.gpu_present:
        return False
    if profile.gpu_vendor not in ("NVIDIA", "AMD"):
        # Integrierte Intel-Grafik zaehlt bewusst nicht als "faehige GPU"
        # fuer lokale LLM-Beschleunigung (siehe Modul-Docstring).
        return False
    if profile.vram_gb is None:
        # Unbekanntes VRAM bei einer dedizierten GPU -> konservativ NICHT
        # als "faehig" werten (kein erfundener Wert, siehe Vorgabe).
        return False
    return profile.vram_gb >= _MIN_CAPABLE_GPU_VRAM_GB


def _is_legacy_cpu(profile: HardwareProfile) -> bool:
    """Konservative, aber begruendete Einordnung: NUR wenn eine bekannte
    Generation UNTER der Schwelle liegt ODER die Kernzahl bekannt und sehr
    niedrig ist, gilt eine CPU als "legacy". Unbekannte Generation/
    Kernzahl fuehrt NICHT automatisch zu "legacy" (das waere ein
    unbegruendetes Urteil ueber evtl. moderne, nur nicht erkannte
    Hardware, z. B. neuere AMD-CPUs ohne Intel-Namensschema)."""
    if profile.cpu_vendor and "Intel" in profile.cpu_vendor and profile.cpu_generation is not None:
        if profile.cpu_generation < _LEGACY_INTEL_GENERATION_THRESHOLD:
            return True
    if profile.cpu_cores is not None and profile.cpu_cores < _LEGACY_MIN_CORES_THRESHOLD:
        return True
    return False


def _nominal_ram_gb(profile: HardwareProfile) -> float | None:
    """Rundet auf die handelsuebliche RAM-Groesse (8/16/32/64 GB ...) statt
    den rohen WMI-Wert direkt zu vergleichen. Echter Fund (§67): ein
    physisch als "16 GB" verkauftes System meldet ueber
    Win32_ComputerSystem.TotalPhysicalMemory oft nur ~15,9 GB (vom BIOS/
    Chipsatz fuer sich reservierter Adressraum) - eine strikte `< 16`-
    Pruefung auf dem Rohwert haette praktisch JEDES reale 16-GB-System
    faelschlich als UNSUPPORTED eingestuft."""
    if profile.ram_total_gb is None:
        return None
    return round(profile.ram_total_gb)


def classify_hardware(profile: HardwareProfile) -> HardwareClass:
    """Deterministische, nachvollziehbare Klassifikation - bewusst NICHT
    nur nach RAM (Vorgabe §67). Reihenfolge der Pruefungen ist Teil der
    Spezifikation, nicht zufaellig."""
    ram_gb = _nominal_ram_gb(profile)
    if ram_gb is None or ram_gb < 16:
        return HardwareClass.UNSUPPORTED

    capable_gpu = has_capable_gpu(profile)

    if capable_gpu:
        if ram_gb >= 64 and (profile.vram_gb or 0) >= 16:
            return HardwareClass.WORKSTATION
        if ram_gb >= 32 and (profile.vram_gb or 0) >= 8:
            return HardwareClass.PERFORMANCE
        return HardwareClass.STANDARD

    # Ab hier: CPU-only (keine GPU oder keine "faehige" GPU).
    if _is_legacy_cpu(profile):
        return HardwareClass.LEGACY
    if ram_gb >= 32:
        return HardwareClass.PERFORMANCE
    return HardwareClass.STANDARD
