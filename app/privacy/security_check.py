"""SecurityCheckService – lokale Sicherheitsprüfung vor jedem geplanten
Claude-API-Aufruf (Architekturvorgabe, Schritt 2 von 5).

Deckt die 7-Punkte-Liste aus der Vorgabe ab:
1. "Welche Daten sollen übertragen werden?" - wird vollständig erst in
   Schritt 3 (Gateway mit Allowlist-Payload-Schema) beantwortet; hier
   bereits durch die Prüfung des konkreten, bereits pseudonymisierten
   Texts abgedeckt.
2/3/4. Enthält der Text (noch) personenbezogene/vertrauliche/nicht
   erlaubte Inhalte? -> erneute PII-Prüfung AUF DEM PSEUDONYMISIERTEN
   TEXT (nicht auf dem Original) - deckt auf, wenn die Pseudonymisierung
   etwas übersehen hat.
5. Wurden alle bekannten Platzhalter korrekt gesetzt? -> jeder
   `PseudonymMapping`-Eintrag muss im Text tatsächlich vorkommen.
6. Gibt es möglicherweise nicht erkannte personenbezogene Daten? ->
   heuristischer Hinweis auf Namens-ähnliche Muster, die keiner bekannten
   Entität entsprechen (siehe `_find_possible_unrecognized_names`).
7. Ist der Aufruf für diese konkrete Aufgabe zulässig? -> `purpose` muss
   in einer festen Allowlist stehen (nur Textproduktions-Aufgaben, siehe
   Architekturvorgabe Punkt 2: "Claude API ausschließlich für
   Textproduktion").

KERNREGEL: "Bei einem nicht eindeutigen Ergebnis: KEIN API-AUFRUF." ->
JEDER gefundene Grund führt zu `passed=False`. Es gibt keinen Modus, der
Warnungen ignoriert und trotzdem grünes Licht gibt.
"""

from __future__ import annotations

import re

from app.privacy.detectors import detect_all
from app.privacy.pseudonymizer import PseudonymMapping
from app.privacy.security_check_schema import SecurityCheckResult

# Nur Textproduktions-Aufgaben - direkte Umsetzung von Vorgabe-Punkt 2.
# Explizit NICHT enthalten: Aktenanalyse, Aktenzuordnung, Rechtsrecherche,
# Fristenbestimmung, Strategieentscheidung, Versand.
ALLOWED_PURPOSES = frozenset(
    {
        "formulate_draft",
        "improve_draft",
        "correct_draft",
        "optimize_style",
        "improve_clarity",
        "apply_house_style",
        "transform_content_to_letter",
        # Review-Engine (Prompt 18): unabhaengige Pruefung eines bereits
        # erstellten Entwurfs - weiterhin reine Textproduktions-/
        # Textanalyse-Aufgabe, keine Rechtsentscheidung.
        "review_draft",
    }
)

# Grobe Heuristik: zwei aufeinanderfolgende großgeschriebene Wörter -
# im Deutschen werden aber ALLE Substantive grossgeschrieben (nicht nur
# Namen), ebenso die Hoeflichkeitsform "Sie/Ihr". Eine reine
# Grossschreibungs-Heuristik wuerde daher in praktisch jedem normalen
# Kanzleibrief false positives erzeugen ("Ihr Schreiben", "Die
# Finanzbehörde" etc.) und den Check dadurch in der Praxis unbrauchbar
# machen. Deshalb: Stoppwortliste haeufiger Formulierungs-/Substantiv-
# Woerter aus dem Kanzlei-/Steuerkontext - wird NUR als Namenskandidat
# gewertet, wenn KEINES der beiden Woerter in dieser Liste steht.
#
# WICHTIGE EINSCHRAENKUNG (ehrlich benannt, siehe ARCHITECTURE.md): Das
# ist weiterhin keine echte NER-Erkennung. Die Liste ist nicht
# erschoepfend - es bleiben sowohl false positives (seltene, hier nicht
# gelistete Substantive) als auch false negatives (ein Name, der zufaellig
# aus zwei gelisteten Woertern besteht) moeglich. Eine zuverlaessigere
# Loesung braucht ein echtes lokales Sprachmodell (siehe TODO.md, Schritt
# 4 / Ollama-Diskussion) - das ist bewusst NICHT Teil dieses Schritts.

_COMMON_GERMAN_FORMAL_WORDS = frozenset(
    {
        # Höflichkeitsform / Pronomen (immer großgeschrieben im Deutschen)
        "ihr", "ihre", "ihrem", "ihren", "ihrer", "ihres", "ihnen", "sie",
        "wir", "uns", "unser", "unsere", "unserem", "unseren", "unserer",
        "unseres", "der", "die", "das", "diese", "dieser", "dieses",
        "diesem", "diesen", "ein", "eine", "einem", "einen", "einer",
        # Haeufige Substantive in Kanzlei-/Steuerkontext
        "schreiben", "kanzlei", "akte", "aktenzeichen", "vertrag",
        "frist", "bescheid", "einspruch", "antrag", "anwalt", "gericht",
        "behörde", "finanzamt", "finanzbehörde", "steuerbescheid",
        "rechnung", "mitteilung", "unterlagen", "dokument", "anlage",
        "betreff", "datum", "angelegenheit", "sachverhalt",
        "stellungnahme", "widerspruch", "bescheinigung", "nachweis",
        "belege", "zahlung", "betrag", "termin", "verfahren", "bezug",
        "damen", "herren", "grüßen", "grüße", "dank", "hinweis",
        "rückfragen", "kenntnisnahme", "prüfung", "übersendung",
        # Anredetitel - kein Namensbestandteil im Sinne dieser Heuristik.
        "herr", "herrn", "frau",
        # Nummerierte Argumentationspunkte (typisch in Schriftsätzen).
        "punkt", "punkte", "erster", "erstens", "zweiter", "zweitens",
        "dritter", "drittens", "vierter", "viertens", "fünfter",
        "fünftens", "letzter", "nächster", "folgender", "obiger",
    }
)


_WORD_PATTERN = re.compile(r"[A-Za-zÄÖÜäöüß]+")


def _find_possible_unrecognized_names(text: str) -> list[str]:
    """Wortbasiertes Scannen statt regex-basiertem Aufeinanderfolgen-Match:
    verhindert, dass ein "verbrauchtes" Wort (z. B. "Herrn" in "Herrn
    Peter") das eigentlich interessante Folgepaar ("Peter Müller")
    unsichtbar macht, weil `re.finditer` keine überlappenden Treffer
    liefert."""
    words = list(_WORD_PATTERN.finditer(text))
    candidates: list[str] = []

    for i in range(len(words) - 1):
        word1, word2 = words[i], words[i + 1]
        between = text[word1.end() : word2.start()]
        if between != " ":
            # Nur direkt durch ein einzelnes Leerzeichen getrennte Wörter
            # gelten als zusammenhaengende Phrase (kein Satzzeichen dazwischen).
            continue
        if not (word1.group()[:1].isupper() and word2.group()[:1].isupper()):
            continue
        if (
            word1.group().lower() in _COMMON_GERMAN_FORMAL_WORDS
            or word2.group().lower() in _COMMON_GERMAN_FORMAL_WORDS
        ):
            continue
        candidates.append(f"{word1.group()} {word2.group()}")

    return candidates


class SecurityCheckService:
    def check(
        self,
        pseudonymized_text: str,
        mappings: list[PseudonymMapping],
        *,
        purpose: str,
    ) -> SecurityCheckResult:
        reasons: list[str] = []

        # Punkt 7: Zweck zulässig?
        if purpose not in ALLOWED_PURPOSES:
            reasons.append(
                f"Zweck '{purpose}' ist nicht in der Allowlist erlaubter "
                f"Textproduktions-Aufgaben ({sorted(ALLOWED_PURPOSES)})"
            )

        # Punkt 2/3/4: erneute PII-Pruefung AUF DEM PSEUDONYMISIERTEN TEXT.
        # Bewusst ohne known_entities - genau diese sollten bereits ersetzt
        # sein; ein Treffer hier bedeutet: etwas wurde uebersehen.
        residual_spans = detect_all(pseudonymized_text)
        if residual_spans:
            categories = sorted({span.category for span in residual_spans})
            reasons.append(
                f"Nach Pseudonymisierung weiterhin erkennbare Muster: {categories}"
            )

        # Punkt 5: jeder Mapping-Eintrag muss im Text tatsächlich vorkommen.
        for mapping in mappings:
            if mapping.placeholder not in pseudonymized_text:
                reasons.append(
                    f"Platzhalter {mapping.placeholder} aus dem Mapping fehlt "
                    "im Text (Inkonsistenz zwischen Mapping und Text)"
                )

        # Punkt 6: heuristischer Hinweis auf evtl. nicht erkannte Namen.
        unclear = _find_possible_unrecognized_names(pseudonymized_text)
        if unclear:
            reasons.append(
                f"Möglicherweise nicht erkannte Namen/Entitäten gefunden: {unclear}"
            )

        return SecurityCheckResult(passed=len(reasons) == 0, reasons=reasons)
