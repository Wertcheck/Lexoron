"""AttorneyInstruction – konkreter Änderungs-/Arbeitsauftrag des Anwalts an
die NÄCHSTE Entwurfsversion.

BEWUSST GETRENNT von `DraftFeedback` (siehe app/models/draft_feedback.py) -
unterschiedliche fachliche Funktion, nicht austauschbar:

- `DraftFeedback` = anwaltliche BEWERTUNG/POSITION zu einem bereits
  vorliegenden Entwurf (Freigabe, Ablehnung, ggf. mit direkter Korrektur).
  Rückblickend.
- `AttorneyInstruction` = ein konkreter Arbeitsauftrag VOR einer
  Neugenerierung ("Auf Punkt 3 eingehen", "§ 286 BGB berücksichtigen").
  Vorausblickend - steuert, was als Nächstes entstehen soll.

`status`:
- "open": gespeichert, aber noch nicht in eine Neugenerierung eingeflossen
  (Dashboard-Aktion "Anmerkung speichern").
- "applied": eine Neugenerierung wurde damit angestoßen und hat
  erfolgreich eine neue Draft-Version erzeugt (`resulting_draft_id`
  gesetzt).
- "discarded": bewusst verworfen, ohne angewendet zu werden (z. B. durch
  eine neuere Anmerkung überholt) - noch kein automatischer Auslöser
  hierfür vorgesehen, das Feld existiert für zukünftige, ausschließlich
  anwaltlich ausgelöste Aktionen.

WICHTIG (Vorgabe des Anwalts, wörtlich): "Claude darf keine anwaltliche
Position erfinden. Eine fehlende anwaltliche Anweisung darf nicht als
Zustimmung, Ablehnung oder sonstige Position interpretiert werden." Ein
FEHLENDER (kein `AttorneyInstruction`-Eintrag zu einem Punkt) oder ein
NOCH NICHT angewendeter ("open") Eintrag darf vom Schreibsystem daher
niemals als inhaltliche Weisung fehlinterpretiert werden - siehe
`app/ai_providers/claude_writing_provider.py: WRITING_SYSTEM_PROMPT` für
die entsprechend verschärfte Systemregel.

Datenschutz: `instruction_text` ist Freitext des Anwalts und kann
personenbezogene/vertrauliche Inhalte enthalten (z. B. Namen, konkrete
Beträge). Er verlässt die lokale Datenbank NUR über
`ClaudePrivacyGateway.prepare_request` (Pseudonymisierung + Security-
Check) - siehe app/attorney_instructions/service.py. Es gibt in diesem
Modell keinen Pfad, der `instruction_text` ungeprüft an eine externe API
weiterreicht.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

VALID_ATTORNEY_INSTRUCTION_STATUSES = ("open", "applied", "discarded")


class AttorneyInstruction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "attorney_instructions"

    # Redundant zu draft.matter_id, aber bewusst direkt gehalten (gleiches
    # Muster wie an anderen Stellen im Projekt, z. B. Deadline.matter_id
    # trotz Document-Bezug) - ermöglicht Aktenisolations-Abfragen auf
    # AttorneyInstruction, ohne zwingend über Draft joinen zu müssen, und
    # bleibt auch dann korrekt, wenn draft_id sich technisch änderte.
    matter_id: Mapped[str] = mapped_column(
        ForeignKey("matters.id"), nullable=False, index=True
    )
    # Die Entwurfsversion, auf die sich die Anmerkung bezieht (der Stand,
    # den der Anwalt beim Verfassen der Anmerkung vor sich hatte).
    draft_id: Mapped[str] = mapped_column(
        ForeignKey("drafts.id"), nullable=False, index=True
    )
    instruction_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default="open", nullable=False
    )
    # Gesetzt, sobald diese Anmerkung tatsächlich zu einer neuen
    # Draft-Version geführt hat (status wechselt dann zu "applied").
    resulting_draft_id: Mapped[str | None] = mapped_column(
        ForeignKey("drafts.id"), nullable=True
    )
    # Freitext wie bei AuditEvent.actor/DraftFeedback.actor (z. B. E-Mail
    # des Anwalts) - bewusst keine strikte FK auf User, konsistent mit
    # DraftFeedback.
    actor: Mapped[str] = mapped_column(String(128), nullable=False)

    draft: Mapped["Draft"] = relationship(foreign_keys=[draft_id])
    resulting_draft: Mapped["Draft | None"] = relationship(
        foreign_keys=[resulting_draft_id]
    )
