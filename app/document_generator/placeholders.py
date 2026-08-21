"""Platzhalter-Definitionen für den Dokumentengenerator (Block 3, 20.08.).

Bewusst KEINE generische Templating-Engine (kein Jinja2/`eval`) - reine
regex-basierte Ersetzung fest definierter, dokumentierter Platzhalter.
Das ist nicht nur einfacher, sondern auch SICHERER (siehe Auftrag: "sicher
... befüllen"): eine echte Templating-Engine würde beliebigen Ausdrücken
in von mehreren Personen (Admin/Anwalt) gepflegten Vorlagen Tür und Tor
öffnen (Server-Side-Template-Injection). Hier ist technisch schlicht
nichts anderes möglich als eine Ersetzung durch vordefinierte Werte -
kein Python-Code, keine Methodenaufrufe, keine Attributzugriffe können
über den Vorlagentext eingeschleust werden.

Zwei Platzhalter-Arten:
1. Einfache Platzhalter `[Name]` (siehe SUPPORTED_PLACEHOLDERS) - werden
   aus Matter/Client/FirmProfile-Feldern befüllt.
2. Gesetzes-Platzhalter `[Paragraf:GESETZ:§NUMMER]` (z. B.
   `[Paragraf:BGB:§ 433]`) - ziehen den tatsächlichen Wortlaut aus der
   digitalen Gesetzesbibliothek (Block 2, app/models/law_section.py).

Ein nicht auflösbarer Platzhalter bleibt UNVERÄNDERT im Text sichtbar
stehen (kein stiller Informationsverlust) - siehe app/document_generator/
service.py: generate_from_template."""

from __future__ import annotations

import re

SIMPLE_PLACEHOLDER_RE = re.compile(r"\[([A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß0-9 ]*)\]")
LAW_PLACEHOLDER_RE = re.compile(r"\[Paragraf:([A-Za-zÄÖÜäöü0-9]+):([^\]]+)\]")

# Name -> menschenlesbare Beschreibung, fuer die Platzhalter-Referenz in
# der Vorlagenverwaltung (templates/document_templates.html).
SUPPORTED_PLACEHOLDERS: dict[str, str] = {
    "Mandantenname": "Name des Mandanten",
    "Mandantennummer": "Mandantennummer",
    "Aktenzeichen": "Aktenzeichen der Akte",
    "Aktentitel": "Titel/Betreff der Akte",
    "Rechtsgebiet": "Rechtsgebiet der Akte (Fallback: des Mandanten)",
    "Kanzleiname": "Name der Kanzlei (Kanzlei-Profil)",
    "Bearbeiter": "Zuständiger Bearbeiter des Mandanten",
    "Datum": "Heutiges Datum (Generierungsdatum)",
}


def extract_placeholders(content: str) -> list[str]:
    """Liefert alle im Text vorkommenden Platzhalter (roh, inkl. Klammern),
    dedupliziert, in Vorkommensreihenfolge - für die Vorschau in der
    Vorlagenverwaltung."""
    seen: list[str] = []
    for pattern in (LAW_PLACEHOLDER_RE, SIMPLE_PLACEHOLDER_RE):
        for match in pattern.finditer(content):
            raw = match.group(0)
            if raw not in seen:
                seen.append(raw)
    return seen
