"""DocumentGeneratorService – füllt eine `DocumentTemplate` mit den Falldaten
einer `Matter` (Block 3, 20.08.). Siehe app/document_generator/__init__.py
für die DSGVO-/Sicherheitsbegründung (kein KI-/Cloud-Aufruf, reine lokale
Textverarbeitung)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.document_generator.placeholders import LAW_PLACEHOLDER_RE, SIMPLE_PLACEHOLDER_RE
from app.firm_profile.service import get_firm_profile
from app.models import AuditEvent, DocumentTemplate, GeneratedDocument, LawSection, Matter


@dataclass
class GenerationResult:
    document: GeneratedDocument
    unresolved_placeholders: list[str]


def _build_context(matter: Matter, db: Session, *, actor_display: str) -> dict[str, str]:
    """Ausschließlich echte Datenbankfelder - siehe Moduldocstring des
    Pakets, warum hier absichtlich KEIN KI-Aufruf und KEIN freier Text
    generiert wird."""
    client = matter.client
    firm_profile = get_firm_profile(db)
    responsible = None
    if client.responsible_user is not None:
        responsible = client.responsible_user.display_name or client.responsible_user.email
    return {
        "Mandantenname": client.name,
        "Mandantennummer": client.client_number or "",
        "Aktenzeichen": matter.reference_number or "",
        "Aktentitel": matter.title or "",
        "Rechtsgebiet": matter.practice_area or client.practice_area or "",
        "Kanzleiname": firm_profile.firm_name or "",
        "Bearbeiter": responsible or actor_display,
        "Datum": date.today().strftime("%d.%m.%Y"),
    }


def _find_law_section(db: Session, law_code: str, raw_section_number: str) -> LawSection | None:
    """Toleranter Abgleich (Leerzeichen ignoriert), damit
    `[Paragraf:BGB:§433]` und `[Paragraf:BGB:§ 433]` gleichermaßen den
    gespeicherten Paragraphen "§ 433" finden."""
    normalized_target = raw_section_number.replace(" ", "").lower()
    candidates = db.query(LawSection).filter(LawSection.law_code == law_code).all()
    for candidate in candidates:
        if candidate.section_number.replace(" ", "").lower() == normalized_target:
            return candidate
    return None


def generate_from_template(
    db: Session, template: DocumentTemplate, matter: Matter, *, actor: str
) -> GenerationResult:
    """Füllt ALLE Platzhalter der Vorlage mit den Falldaten GENAU EINER
    Akte (Aktenisolation) - persistiert das Ergebnis als neues
    `GeneratedDocument` und protokolliert die Generierung als
    `AuditEvent`."""
    context = _build_context(matter, db, actor_display=actor)
    unresolved: list[str] = []

    def _replace_law(match: re.Match[str]) -> str:
        law_code, raw_section_number = match.group(1), match.group(2)
        section = _find_law_section(db, law_code, raw_section_number)
        if section is None:
            unresolved.append(match.group(0))
            return match.group(0)
        return f"{section.section_number} {section.law_code} ({section.title}): „{section.text_content}“"

    def _replace_simple(match: re.Match[str]) -> str:
        name = match.group(1)
        value = context.get(name)
        if not value:
            unresolved.append(match.group(0))
            return match.group(0)
        return value

    text = LAW_PLACEHOLDER_RE.sub(_replace_law, template.content)
    text = SIMPLE_PLACEHOLDER_RE.sub(_replace_simple, text)

    document = GeneratedDocument(
        template_id=template.id,
        matter_id=matter.id,
        title=f"{template.name} – {matter.title}",
        content=text,
        unresolved_placeholders_json=json.dumps(unresolved, ensure_ascii=False),
        created_by_actor=actor,
        updated_by_actor=actor,
    )
    db.add(document)
    db.flush()
    detail = f"Aus Vorlage '{template.name}' für Akte '{matter.title}' generiert"
    if unresolved:
        detail += f" - {len(unresolved)} Platzhalter nicht auflösbar: {', '.join(unresolved)}"
    db.add(
        AuditEvent(
            entity_type="GeneratedDocument",
            entity_id=document.id,
            event_type="document_generated",
            actor=actor,
            details=detail,
        )
    )
    db.commit()
    db.refresh(document)
    return GenerationResult(document=document, unresolved_placeholders=unresolved)


def get_unresolved_placeholders(document: GeneratedDocument) -> list[str]:
    if not document.unresolved_placeholders_json:
        return []
    return json.loads(document.unresolved_placeholders_json)


def update_content(
    db: Session, document: GeneratedDocument, content: str, *, actor: str
) -> GeneratedDocument:
    document.content = content
    document.updated_by_actor = actor
    db.add(
        AuditEvent(
            entity_type="GeneratedDocument",
            entity_id=document.id,
            event_type="document_edited",
            actor=actor,
            details="Manuell bearbeitet",
        )
    )
    db.commit()
    db.refresh(document)
    return document
