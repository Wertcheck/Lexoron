"""Prompt-/Policy-Layer (Prompt 16).

Trennt strikt: Systemregeln (fest, versioniert), Kanzleiregeln (Policy,
Prompt-16-Modell, versioniert), Fallkontext (strikt aktenbezogen, IMMER
über `matter_id` gefiltert), Rechtsquellen (aus Prompt 15) und
Benutzeranweisung. Baut noch KEINEN Aufruf an ein LLM auf - das entsteht
erst mit der Modell-Anbindung (Prompt 17/34). Dieser Layer bereitet nur
den strukturierten, geprüften Kontext vor, den ein späterer LLM-Aufruf
dann als Eingabe bekäme.

WICHTIGSTE REGEL (Konzept Prompt 16, wörtlich): "Verhindere, dass
Mandantendaten aus einer anderen Akte in den Kontext gelangen." -
`PromptContextBuilder.build_context` verlangt daher zwingend `matter_id`
und filtert JEDE Datenabfrage danach (siehe app/promptlayer/builder.py).

Jede `PromptSection` markiert zusätzlich, ob sie vertrauenswürdige
Anweisung (System, Kanzleiregeln, Benutzeranweisung) oder potenziell
nicht-vertrauenswürdigen externen Inhalt (Fallkontext, Rechtsquellen)
enthält - Grundlage für den Prompt-Injection-Schutz aus Prompt 28.
"""

from app.promptlayer.builder import PromptContextBuilder
from app.promptlayer.policy_service import PolicyService
from app.promptlayer.schema import PromptContext, PromptSection

__all__ = [
    "PromptContextBuilder",
    "PolicyService",
    "PromptContext",
    "PromptSection",
]
