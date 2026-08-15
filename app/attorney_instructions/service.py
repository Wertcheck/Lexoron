"""AttorneyInstructionService – anwaltliche Anmerkungen speichern und
(getrennt) auf eine Neugenerierung anwenden.

Bewusst ZWEI getrennte Methoden, analog zum Muster von
`DraftFeedbackService` (Speichern vs. Kanzleiwissen-Übernahme sind dort
ebenfalls getrennt):

- `create_instruction`: legt NUR einen `AttorneyInstruction`-Eintrag an
  (status="open"). Löst KEINE Claude-Anfrage aus. Entspricht der
  Dashboard-Aktion "Anmerkung speichern".
- `apply_instruction`: löst tatsächlich eine Neugenerierung aus -
  delegiert an `DraftingService.create_draft(previous_draft=...,
  attorney_anmerkungen=...)`, das seinerseits den vollständigen Privacy-
  Gateway-Durchlauf erzwingt (siehe app/privacy/gateway.py - unverändert,
  hier nicht dupliziert). Entspricht der Dashboard-Aktion "Änderungen
  übernehmen & neu formulieren".

WICHTIG (Datenschutz, Vorgabe des Anwalts, wörtlich): "AttorneyInstruction
darf niemals ungeprüft an Claude gehen." Dieser Service selbst ruft KEINE
Claude API auf und pseudonymisiert NICHTS eigenständig - `instruction_text`
wird unverändert an `DraftingService.create_draft` durchgereicht, das ihn
ausschließlich über `ClaudePrivacyGateway.prepare_request` (Pseudonymisierung
+ SecurityCheckService) leitet, bevor irgendetwas den Prozess verlässt. Es
gibt in diesem Service keine zweite, daran vorbeiführende Code-Zeile.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.attorney_instructions.schema import ApplyInstructionResult, AttorneyInstructionInput
from app.drafting.service import DraftingService
from app.models import AttorneyInstruction, AuditEvent, Draft


class AttorneyInstructionService:
    def __init__(self, drafting_service: DraftingService | None = None) -> None:
        """`drafting_service=None` ist bewusst zulässig: `create_instruction`
        (nur speichern) verwendet ihn NIE - nur `apply_instruction`
        (Neugenerierung) braucht ihn tatsächlich und prüft das explizit.
        Das erlaubt der aufrufenden Web-Schicht (app/web/drafts_router.py),
        für die reine "Anmerkung speichern"-Aktion einen leichtgewichtigen
        Service ohne teure Claude-/Embedding-Provider-Initialisierung zu
        bauen, statt bei jedem Speichern unnötig einen vollständigen
        `DraftingService` (inkl. Prüfung auf konfigurierten Claude-API-Key)
        aufzubauen."""
        self.drafting_service = drafting_service

    def create_instruction(
        self,
        draft: Draft,
        data: AttorneyInstructionInput,
        db: Session,
        *,
        actor: str,
    ) -> AttorneyInstruction:
        """Speichert eine Anmerkung, OHNE eine Neugenerierung anzustoßen."""
        instruction = AttorneyInstruction(
            matter_id=draft.matter_id,
            draft_id=draft.id,
            instruction_text=data.instruction_text,
            status="open",
            actor=actor,
        )
        db.add(instruction)
        db.flush()

        db.add(
            AuditEvent(
                entity_type="AttorneyInstruction",
                entity_id=instruction.id,
                event_type="attorney_instruction_created",
                actor=actor,
                details=f"Anmerkung zu Draft {draft.id} gespeichert",
            )
        )
        db.commit()
        db.refresh(instruction)
        return instruction

    def apply_instruction(
        self,
        instruction: AttorneyInstruction,
        db: Session,
        *,
        purpose: str,
        actor: str,
        stil: str | None = None,
        vorlage: str | None = None,
    ) -> ApplyInstructionResult:
        """Löst eine Neugenerierung auf Basis der Anmerkung aus.

        Nur bei Erfolg (`drafting_result.success=True`) wird die
        Anmerkung als "applied" markiert und mit der neuen Draft-Version
        verknüpft (`resulting_draft_id`) - bei Blockierung durch den
        Privacy Gateway oder einem Fehler bei der Textproduktion bleibt
        sie unverändert "open" (nichts wurde tatsächlich angewendet).

        Design-Entscheidung (siehe Analyse vor Freigabe): die Neugenerierung
        baut den Aktenkontext (Sachverhalt/Quellen/Wissen) unverändert aus
        den AKTUELLEN Aktendaten neu auf - sie erhält NICHT zusätzlich den
        Text der vorherigen Draft-Version als Eingabe (die Allowlist-
        Erweiterung ist bewusst auf GENAU EIN neues Feld beschränkt, siehe
        gateway_schema.py). Die Anmerkung selbst steuert die Neuformulierung.
        Für Anmerkungen, die wörtlich auf den bisherigen Text Bezug nehmen
        (z. B. "diesen Absatz streichen"), ist das eine bekannte Grenze -
        siehe offene Punkte im Abschlussbericht.
        """
        if instruction.status != "open":
            raise ValueError(
                f"AttorneyInstruction {instruction.id} hat Status "
                f"'{instruction.status}' - nur 'open' kann angewendet werden"
            )
        if self.drafting_service is None:
            raise ValueError(
                "apply_instruction erfordert einen konfigurierten "
                "DraftingService - dieser Service wurde ohne einen "
                "erstellt (siehe AttorneyInstructionService.__init__)"
            )

        drafting_result = self.drafting_service.create_draft(
            instruction.matter_id,
            purpose,
            db,
            stil=stil,
            vorlage=vorlage,
            attorney_anmerkungen=instruction.instruction_text,
            previous_draft=instruction.draft,
            actor=actor,
        )

        if not drafting_result.success or not drafting_result.draft_id:
            # Bewusst KEIN Statuswechsel - ein gescheiterter Versuch bleibt
            # "open" und kann erneut versucht werden.
            db.add(
                AuditEvent(
                    entity_type="AttorneyInstruction",
                    entity_id=instruction.id,
                    event_type="attorney_instruction_apply_failed",
                    actor=actor,
                    details=(
                        "Neugenerierung fehlgeschlagen/blockiert: "
                        f"{'; '.join(drafting_result.blocked_reasons) or 'unbekannter Fehler'}"
                    ),
                )
            )
            db.commit()
            return ApplyInstructionResult(
                instruction=instruction, drafting_result=drafting_result, new_draft=None
            )

        new_draft = db.get(Draft, drafting_result.draft_id)

        instruction.status = "applied"
        instruction.resulting_draft_id = drafting_result.draft_id

        db.add(
            AuditEvent(
                entity_type="AttorneyInstruction",
                entity_id=instruction.id,
                event_type="attorney_instruction_applied",
                actor=actor,
                details=f"Neue Draft-Version {drafting_result.draft_id} erzeugt",
            )
        )
        db.commit()
        db.refresh(instruction)

        return ApplyInstructionResult(
            instruction=instruction, drafting_result=drafting_result, new_draft=new_draft
        )
