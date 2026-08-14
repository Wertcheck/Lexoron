"""Privacy-Schicht (Architekturerweiterung nach Prompt 16, vor Prompt 17).

Dies ist der erste, kleinste Baustein des vom Anwalt vorgegebenen
Local-First-/Privacy-by-Design-Prinzips: PII-Erkennung und
Pseudonymisierung. NOCH NICHT enthalten (folgen als eigene, spätere
Schritte): Security-Check, `ClaudePrivacyGateway`-Orchestrierung,
`LocalAIProvider`/`ClaudeWritingProvider`, tatsächlicher Claude-API-Aufruf.

WICHTIGE EINSCHRÄNKUNG, ehrlich benannt (siehe ARCHITECTURE.md): Reine
Namens-Erkennung per Regex/NLP ohne echtes NER-Modell ist unzuverlässig.
Deshalb kombiniert dieses Modul zwei Strategien:
1. Regex-Erkennung für strukturierte Formate (E-Mail, Telefon, IBAN,
   Steuer-ID, Aktenzeichen, Kundennummer, Datum, Betrag) - deterministisch,
   kein LLM.
2. Bekannte Entitäten (`known_entities`): Namen/Adressen, die der
   Aufrufer aus bereits vorhandenen strukturierten Daten (Party.name,
   Client.name, Matter.reference_number) mitgibt - zuverlässiger als
   freies Raten, weil wir diese Werte in unserem Fall bereits kennen.

Diese Kombination ersetzt NICHT den in Punkt 6 der Vorgabe geforderten
Security-Check ("nicht erkannte/unklare Daten" als eigener Prüfpunkt) -
das bleibt bewusst ein separater, nachgelagerter Schritt.
"""

from app.privacy.detectors import DetectedSpan, detect_all
from app.privacy.pseudonymizer import PseudonymMapping, Pseudonymizer

__all__ = ["DetectedSpan", "detect_all", "PseudonymMapping", "Pseudonymizer"]
