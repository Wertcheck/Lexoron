"""Tests für app/document_generator/service.py (Dokumenten-/Schriftsatz-
Generator, Block 3, 20.08.)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.document_generator.placeholders import extract_placeholders
from app.document_generator.service import (
    generate_from_template,
    get_unresolved_placeholders,
    update_content,
)
from app.laws.service import import_law_fixture_data
from app.models import AuditEvent, Client, DocumentTemplate, GeneratedDocument, Matter
from app.models.base import Base


@pytest.fixture()
def db_session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _matter_with_client(db: Session, **client_kwargs) -> Matter:
    defaults = {"name": "Muster GmbH", "client_number": "M-1", "practice_area": "Mietrecht"}
    defaults.update(client_kwargs)
    client = Client(**defaults)
    db.add(client)
    db.flush()
    matter = Matter(
        client_id=client.id,
        title="Kündigungsschutzklage",
        status="open",
        reference_number="AZ-100/26",
        practice_area="Arbeitsrecht",
    )
    db.add(matter)
    db.commit()
    db.refresh(matter)
    return matter


def _template(db: Session, content: str) -> DocumentTemplate:
    template = DocumentTemplate(name="Testvorlage", content=content, version=1)
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


# --- Grundlegende Platzhalter-Auflösung ---


def test_generate_fills_client_and_matter_placeholders(db_session: Session) -> None:
    matter = _matter_with_client(db_session)
    template = _template(
        db_session,
        "Sehr geehrte/r [Mandantenname],\n\nin der Sache [Aktenzeichen] ([Aktentitel]).",
    )
    result = generate_from_template(db_session, template, matter, actor="anwalt@kanzlei.test")

    assert "Muster GmbH" in result.document.content
    assert "AZ-100/26" in result.document.content
    assert "Kündigungsschutzklage" in result.document.content
    assert result.unresolved_placeholders == []


def test_generate_falls_back_to_client_practice_area_when_matter_has_none(
    db_session: Session,
) -> None:
    client = Client(name="Muster GmbH", client_number="M-2", practice_area="Erbrecht")
    db_session.add(client)
    db_session.flush()
    matter = Matter(client_id=client.id, title="Akte ohne Rechtsgebiet", status="open")
    db_session.add(matter)
    db_session.commit()

    template = _template(db_session, "Rechtsgebiet: [Rechtsgebiet]")
    result = generate_from_template(db_session, template, matter, actor="anwalt@kanzlei.test")
    assert "Erbrecht" in result.document.content


def test_generate_leaves_unresolved_placeholder_visible_in_text(db_session: Session) -> None:
    """Kernanforderung ("sicher... befüllen"): ein nicht auflösbarer
    Platzhalter darf NICHT stillschweigend verschwinden."""
    matter = _matter_with_client(db_session)
    template = _template(db_session, "Betreuer: [NichtUnterstuetzterPlatzhalter]")
    result = generate_from_template(db_session, template, matter, actor="anwalt@kanzlei.test")

    assert "[NichtUnterstuetzterPlatzhalter]" in result.document.content
    assert result.unresolved_placeholders == ["[NichtUnterstuetzterPlatzhalter]"]
    assert get_unresolved_placeholders(result.document) == ["[NichtUnterstuetzterPlatzhalter]"]


def test_generate_marks_empty_field_as_unresolved_instead_of_blank(db_session: Session) -> None:
    client = Client(name="Muster GmbH", client_number="M-3")
    db_session.add(client)
    db_session.flush()
    matter = Matter(client_id=client.id, title="Akte ohne Aktenzeichen", status="open")
    db_session.add(matter)
    db_session.commit()

    template = _template(db_session, "Aktenzeichen: [Aktenzeichen]")
    result = generate_from_template(db_session, template, matter, actor="anwalt@kanzlei.test")
    assert "[Aktenzeichen]" in result.document.content
    assert "[Aktenzeichen]" in result.unresolved_placeholders


def test_generate_uses_responsible_user_display_name_for_bearbeiter(db_session: Session) -> None:
    from app.models import Role, User

    role = Role(name="Anwalt")
    db_session.add(role)
    db_session.flush()
    user = User(email="anna@kanzlei.test", display_name="Anna Beispiel", role_id=role.id)
    db_session.add(user)
    db_session.flush()

    client = Client(name="Muster GmbH", client_number="M-4", responsible_user_id=user.id)
    db_session.add(client)
    db_session.flush()
    matter = Matter(client_id=client.id, title="Akte", status="open")
    db_session.add(matter)
    db_session.commit()

    template = _template(db_session, "Bearbeiter: [Bearbeiter]")
    result = generate_from_template(db_session, template, matter, actor="admin@kanzlei.test")
    assert "Anna Beispiel" in result.document.content


def test_generate_falls_back_to_actor_when_no_responsible_user(db_session: Session) -> None:
    matter = _matter_with_client(db_session)
    template = _template(db_session, "Bearbeiter: [Bearbeiter]")
    result = generate_from_template(db_session, template, matter, actor="admin@kanzlei.test")
    assert "admin@kanzlei.test" in result.document.content


# --- Gesetzes-Platzhalter (Integration mit Block 2) ---


def test_generate_resolves_law_placeholder_with_full_text(db_session: Session) -> None:
    import_law_fixture_data(
        db_session,
        {
            "code": "BGB",
            "title": "Bürgerliches Gesetzbuch",
            "sections": [
                {
                    "section_number": "§ 985",
                    "title": "Herausgabeanspruch",
                    "text_content": "Der Eigentümer kann von dem Besitzer die Herausgabe der Sache verlangen.",
                    "last_updated": "2026-08-20",
                }
            ],
        },
    )
    matter = _matter_with_client(db_session)
    template = _template(db_session, "Rechtsgrundlage: [Paragraf:BGB:§ 985]")
    result = generate_from_template(db_session, template, matter, actor="anwalt@kanzlei.test")

    assert "§ 985 BGB" in result.document.content
    assert "Herausgabeanspruch" in result.document.content
    assert "Der Eigentümer kann von dem Besitzer die Herausgabe der Sache verlangen." in result.document.content
    assert result.unresolved_placeholders == []


def test_generate_law_placeholder_tolerates_missing_space_in_section_number(
    db_session: Session,
) -> None:
    import_law_fixture_data(
        db_session,
        {
            "code": "StGB",
            "title": "Strafgesetzbuch",
            "sections": [
                {
                    "section_number": "§ 242",
                    "title": "Diebstahl",
                    "text_content": "Wer eine fremde bewegliche Sache wegnimmt...",
                    "last_updated": "2026-08-20",
                }
            ],
        },
    )
    matter = _matter_with_client(db_session)
    template = _template(db_session, "Vorwurf: [Paragraf:StGB:§242]")
    result = generate_from_template(db_session, template, matter, actor="anwalt@kanzlei.test")
    assert "Diebstahl" in result.document.content
    assert result.unresolved_placeholders == []


def test_generate_leaves_unknown_law_placeholder_unresolved(db_session: Session) -> None:
    matter = _matter_with_client(db_session)
    template = _template(db_session, "Vorschrift: [Paragraf:BGB:§ 999999]")
    result = generate_from_template(db_session, template, matter, actor="anwalt@kanzlei.test")
    assert "[Paragraf:BGB:§ 999999]" in result.document.content
    assert result.unresolved_placeholders == ["[Paragraf:BGB:§ 999999]"]


# --- Persistenz / Audit ---


def test_generate_persists_document_and_writes_audit_event(db_session: Session) -> None:
    matter = _matter_with_client(db_session)
    template = _template(db_session, "Mandant: [Mandantenname]")
    result = generate_from_template(db_session, template, matter, actor="anwalt@kanzlei.test")

    assert db_session.query(GeneratedDocument).count() == 1
    stored = db_session.get(GeneratedDocument, result.document.id)
    assert stored is not None
    assert stored.matter_id == matter.id
    assert stored.template_id == template.id

    events = db_session.query(AuditEvent).filter_by(entity_id=result.document.id).all()
    assert any(e.event_type == "document_generated" for e in events)


def test_update_content_saves_edit_and_writes_audit_event(db_session: Session) -> None:
    matter = _matter_with_client(db_session)
    template = _template(db_session, "Mandant: [Mandantenname]")
    result = generate_from_template(db_session, template, matter, actor="anwalt@kanzlei.test")

    updated = update_content(
        db_session, result.document, "Manuell überarbeiteter Text.", actor="anwalt@kanzlei.test"
    )
    assert updated.content == "Manuell überarbeiteter Text."

    events = db_session.query(AuditEvent).filter_by(entity_id=result.document.id).all()
    assert any(e.event_type == "document_edited" for e in events)


def test_generate_never_makes_network_calls(db_session: Session) -> None:
    """Kern der DSGVO-Anforderung: die Generierung ist rein lokale
    Textverarbeitung - kein KI-/Cloud-Aufruf, egal was die Vorlage enthält."""
    from unittest.mock import patch

    matter = _matter_with_client(db_session)
    template = _template(
        db_session, "[Mandantenname], [Aktenzeichen], [Paragraf:BGB:§ 1], [NichtVorhanden]"
    )
    with patch("httpx.Client.request") as mock_request:
        generate_from_template(db_session, template, matter, actor="anwalt@kanzlei.test")
        mock_request.assert_not_called()


# --- extract_placeholders (Vorlagen-Übersicht) ---


def test_extract_placeholders_deduplicates_and_preserves_order() -> None:
    content = "[Mandantenname] ... [Aktenzeichen] ... [Mandantenname] wieder"
    assert extract_placeholders(content) == ["[Mandantenname]", "[Aktenzeichen]"]


def test_extract_placeholders_recognizes_law_placeholder_separately() -> None:
    content = "[Mandantenname], [Paragraf:BGB:§ 433]"
    result = extract_placeholders(content)
    assert "[Mandantenname]" in result
    assert "[Paragraf:BGB:§ 433]" in result
