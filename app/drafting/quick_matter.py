"""create_quick_matter – gemeinsame Hilfsfunktion für die automatische
Akten-/Mandantenanlage, wenn eine Entwurfserstellung ohne Aktenauswahl
angestoßen wird (Schriftsatz-Generator, 20.08.).

Wird von ZWEI Stellen genutzt:
- `DraftingService.create_draft` (app/drafting/service.py), wenn
  `matter_id=None` übergeben wird.
- `app/web/schriftsatz_router.py` direkt, WEIL dort Drag&Drop-Dokumente vor
  dem eigentlichen `create_draft`-Aufruf als `Document` gespeichert werden
  müssen (damit `RuleBasedLocalAIProvider.prepare_draft_context` sie
  überhaupt sieht) - das setzt voraus, dass die Akte zu diesem Zeitpunkt
  bereits existiert. Der Router löst die Akte deshalb selbst VORAB auf und
  übergibt anschließend eine echte `matter_id` an `create_draft` (dessen
  eigener Auto-Create-Zweig bleibt trotzdem bestehen, für alle anderen/
  zukünftigen Aufrufer ohne Aktenauswahl, z. B. eine spätere API).

Eine einzige, gemeinsame Stelle statt zweier fast identischer
Implementierungen - Aktenanlage ist sicherheitsrelevant genug (Aktenisolation,
Audit), um hier keine Kopie driften zu lassen."""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.models import AuditEvent, Client, Matter


def create_quick_matter(
    db: Session, *, title: str | None, client_name: str | None, actor: str
) -> Matter:
    """Legt einen neuen `Client` + eine neue `Matter` (Status "open") an und
    committet sofort - der Aufrufer erhält eine sofort nutzbare `matter.id`.
    Schreibt ein `AuditEvent` (`matter_auto_created`), damit diese
    automatische, für den Anwalt nicht offensichtliche Nebenwirkung
    nachvollziehbar bleibt (siehe CLAUDE.md-Grundregel zu KI-Aktionen)."""
    client = Client(name=client_name or "Ohne Mandantenzuordnung")
    db.add(client)
    db.flush()  # client.id fuer die neue Matter benoetigt

    matter = Matter(
        client_id=client.id,
        title=title or f"Schnellentwurf {date.today().isoformat()}",
        status="open",
    )
    db.add(matter)
    db.flush()  # matter.id fuer das AuditEvent/den weiteren Ablauf benoetigt

    db.add(
        AuditEvent(
            entity_type="Matter",
            entity_id=matter.id,
            event_type="matter_auto_created",
            actor=actor,
            details=(
                f"Akte automatisch angelegt (ohne Aktenauswahl), "
                f"Mandant: {client.name}"
            ),
        )
    )
    db.commit()
    return matter
