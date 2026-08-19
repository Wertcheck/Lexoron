"""Tests für DraftQualityService (Prompt 43 – Anwalts-Feedbackschleife)."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models import (
    Base,
    Client,
    Draft,
    DraftQualityRating,
    Matter,
    User,
    Role,
)
from app.quality.schema import DraftQualityRatingInput
from app.quality.service import DraftQualityService


@pytest.fixture
def test_session() -> Session:
    """In-Memory SQLite Test-Datenbank."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session_ = sessionmaker(bind=engine)
    session = Session_()
    yield session
    session.close()


@pytest.fixture
def test_data(test_session: Session) -> dict:
    """Teste Daten: Client, Matter, User, Draft."""
    # Client
    client = Client(id="client1", name="Testmandant")
    test_session.add(client)
    
    # User (Anwalt + für "rated_by")
    role = Role(id="attorney", name="Attorney")
    attorney = User(
        id="attorney1",
        email="attorney@test.local",
        password_hash="dummy",
        role_id="attorney",
    )
    test_session.add(role)
    test_session.add(attorney)
    
    # Matter
    matter = Matter(
        id="matter1",
        client_id="client1",
        title="Testakte 1",
        reference_number="AZ-2024-001",
    )
    test_session.add(matter)
    
    # Draft (mit Status "approved")
    draft_approved = Draft(
        id="draft_approved_1",
        matter_id="matter1",
        content="Dies ist ein genehmigter Entwurf.",
        status="approved",
    )
    test_session.add(draft_approved)
    
    # Draft (mit Status "draft" – darf nicht bewertet werden)
    draft_unapproved = Draft(
        id="draft_draft_1",
        matter_id="matter1",
        content="Dies ist ein ungenehmigter Entwurf.",
        status="draft",
    )
    test_session.add(draft_unapproved)
    
    test_session.commit()
    
    return {
        "test_session": test_session,
        "client": client,
        "matter": matter,
        "attorney": attorney,
        "draft_approved": draft_approved,
        "draft_unapproved": draft_unapproved,
    }


class TestDraftQualityRatingRecord:
    """Tests für das Speichern von Bewertungen."""
    
    def test_record_rating_with_all_scales(self, test_data: dict):
        """Bewertung mit allen vier Skalen speichern."""
        service = DraftQualityService(test_data["test_session"])
        
        input_data = DraftQualityRatingInput(
            content_quality=5,
            usefulness=4,
            completeness=5,
            language_quality=4,
        )
        
        rating = service.record_rating(
            draft_id="draft_approved_1",
            rated_by_user_id="attorney1",
            input_data=input_data,
        )
        
        assert rating.draft_id == "draft_approved_1"
        assert rating.rated_by_user_id == "attorney1"
        assert rating.content_quality == 5
        assert rating.usefulness == 4
        assert rating.completeness == 5
        assert rating.language_quality == 4
        assert rating.comment is None
    
    def test_record_rating_with_comment_only(self, test_data: dict):
        """Bewertung mit nur Kommentar (keine numerischen Skalen)."""
        service = DraftQualityService(test_data["test_session"])
        
        input_data = DraftQualityRatingInput(
            comment="Guter Entwurf, aber ein paar kleine Formulierungen könnten optimiert werden."
        )
        
        rating = service.record_rating(
            draft_id="draft_approved_1",
            rated_by_user_id="attorney1",
            input_data=input_data,
        )
        
        assert rating.content_quality is None
        assert rating.comment == "Guter Entwurf, aber ein paar kleine Formulierungen könnten optimiert werden."
    
    def test_record_rating_with_mixed_data(self, test_data: dict):
        """Bewertung mit Mischung aus Skalen und Kommentar."""
        service = DraftQualityService(test_data["test_session"])
        
        input_data = DraftQualityRatingInput(
            content_quality=4,
            usefulness=5,
            comment="Sehr nützlich!",
        )
        
        rating = service.record_rating(
            draft_id="draft_approved_1",
            rated_by_user_id="attorney1",
            input_data=input_data,
        )
        
        assert rating.content_quality == 4
        assert rating.usefulness == 5
        assert rating.completeness is None
        assert rating.language_quality is None
        assert rating.comment == "Sehr nützlich!"
    
    def test_record_rating_empty_input_fails(self, test_data: dict):
        """Leere Bewertung (alle Felder leer) wird abgelehnt."""
        service = DraftQualityService(test_data["test_session"])
        
        input_data = DraftQualityRatingInput()  # Alle Felder leer
        
        with pytest.raises(ValueError, match="Bewertung muss mindestens"):
            service.record_rating(
                draft_id="draft_approved_1",
                rated_by_user_id="attorney1",
                input_data=input_data,
            )
    
    def test_record_rating_nonexistent_draft_fails(self, test_data: dict):
        """Bewertung für nicht existierenden Entwurf wird abgelehnt."""
        service = DraftQualityService(test_data["test_session"])
        
        input_data = DraftQualityRatingInput(content_quality=3)
        
        with pytest.raises(ValueError, match="Entwurf .* nicht gefunden"):
            service.record_rating(
                draft_id="nonexistent_draft",
                rated_by_user_id="attorney1",
                input_data=input_data,
            )
    
    def test_record_rating_unapproved_draft_fails(self, test_data: dict):
        """Bewertung für ungenehmigten Entwurf wird abgelehnt."""
        service = DraftQualityService(test_data["test_session"])
        
        input_data = DraftQualityRatingInput(content_quality=3)
        
        with pytest.raises(ValueError, match="Status 'approved'"):
            service.record_rating(
                draft_id="draft_draft_1",
                rated_by_user_id="attorney1",
                input_data=input_data,
            )
    
    def test_multiple_ratings_same_draft(self, test_data: dict):
        """Mehrere Bewertungen zum selben Entwurf von verschiedenen Nutzern."""
        session = test_data["test_session"]
        
        # Zweiter Nutzer hinzufügen
        attorney2 = User(
            id="attorney2",
            email="attorney2@test.local",
            password_hash="dummy",
            role_id="attorney",
        )
        session.add(attorney2)
        session.commit()
        
        service = DraftQualityService(session)
        
        # Erste Bewertung
        rating1 = service.record_rating(
            draft_id="draft_approved_1",
            rated_by_user_id="attorney1",
            input_data=DraftQualityRatingInput(content_quality=5),
        )
        
        # Zweite Bewertung (von anderem Nutzer)
        rating2 = service.record_rating(
            draft_id="draft_approved_1",
            rated_by_user_id="attorney2",
            input_data=DraftQualityRatingInput(content_quality=3),
        )
        
        # Beide Bewertungen sollten gespeichert sein
        assert rating1.id != rating2.id
        assert rating1.rated_by_user_id == "attorney1"
        assert rating2.rated_by_user_id == "attorney2"


class TestDraftQualityRatingRetrival:
    """Tests für das Abrufen von Bewertungen."""
    
    def test_get_ratings_for_draft(self, test_data: dict):
        """Alle Bewertungen für einen Entwurf abrufen."""
        session = test_data["test_session"]
        service = DraftQualityService(session)
        
        # Mehrere Bewertungen speichern
        for i in range(3):
            service.record_rating(
                draft_id="draft_approved_1",
                rated_by_user_id="attorney1",
                input_data=DraftQualityRatingInput(content_quality=i+1),
            )
        
        ratings = service.get_ratings_for_draft("draft_approved_1")
        assert len(ratings) == 3
        # Sollten sortiert sein (neueste zuerst)
        assert ratings[0].content_quality == 3
        assert ratings[1].content_quality == 2
        assert ratings[2].content_quality == 1
    
    def test_get_ratings_nonexistent_draft(self, test_data: dict):
        """Keine Bewertungen für nicht existierenden Entwurf."""
        service = DraftQualityService(test_data["test_session"])
        ratings = service.get_ratings_for_draft("nonexistent")
        assert len(ratings) == 0


class TestDraftQualityStats:
    """Tests für Statistik-Berechnungen."""
    
    def test_compute_stats_single_rating(self, test_data: dict):
        """Statistiken mit einer einzelnen Bewertung."""
        session = test_data["test_session"]
        service = DraftQualityService(session)
        
        service.record_rating(
            draft_id="draft_approved_1",
            rated_by_user_id="attorney1",
            input_data=DraftQualityRatingInput(
                content_quality=4,
                usefulness=5,
                completeness=3,
                language_quality=4,
            ),
        )
        
        stats = service.compute_stats("draft_approved_1")
        
        assert stats.draft_id == "draft_approved_1"
        assert stats.total_ratings == 1
        assert stats.avg_content_quality == 4.0
        assert stats.avg_usefulness == 5.0
        assert stats.avg_completeness == 3.0
        assert stats.avg_language_quality == 4.0
        # Durchschnitt aller vier: (4+5+3+4)/4 = 4.0
        assert stats.avg_overall == 4.0
    
    def test_compute_stats_multiple_ratings(self, test_data: dict):
        """Statistiken mit mehreren Bewertungen."""
        session = test_data["test_session"]
        
        # Zweiter Nutzer
        attorney2 = User(
            id="attorney2",
            email="attorney2@test.local",
            password_hash="dummy",
            role_id="attorney",
        )
        session.add(attorney2)
        session.commit()
        
        service = DraftQualityService(session)
        
        # Bewertung 1: alle Skalen
        service.record_rating(
            draft_id="draft_approved_1",
            rated_by_user_id="attorney1",
            input_data=DraftQualityRatingInput(
                content_quality=5,
                usefulness=4,
                completeness=5,
                language_quality=4,
            ),
        )
        
        # Bewertung 2: nur content_quality
        service.record_rating(
            draft_id="draft_approved_1",
            rated_by_user_id="attorney2",
            input_data=DraftQualityRatingInput(content_quality=3),
        )
        
        stats = service.compute_stats("draft_approved_1")
        
        assert stats.total_ratings == 2
        # content_quality: (5+3)/2 = 4.0
        assert stats.avg_content_quality == 4.0
        # usefulness: nur eine Bewertung (4)
        assert stats.avg_usefulness == 4.0
        # Gesamtdurchschnitt: (4.0+4.0+5.0+4.0)/4 = 4.25
        assert stats.avg_overall == 4.25
    
    def test_compute_stats_no_ratings(self, test_data: dict):
        """Statistiken wenn keine Bewertungen vorhanden sind."""
        service = DraftQualityService(test_data["test_session"])
        
        stats = service.compute_stats("draft_approved_1")
        
        assert stats.total_ratings == 0
        assert stats.avg_content_quality is None
        assert stats.avg_usefulness is None
        assert stats.avg_overall is None
    
    def test_compute_stats_partial_ratings(self, test_data: dict):
        """Statistiken wenn nur einzelne Skalen bewertet wurden."""
        session = test_data["test_session"]
        service = DraftQualityService(session)
        
        # Bewertung mit nur zwei Skalen
        service.record_rating(
            draft_id="draft_approved_1",
            rated_by_user_id="attorney1",
            input_data=DraftQualityRatingInput(
                content_quality=5,
                usefulness=3,
                # completeness und language_quality bleiben None
            ),
        )
        
        stats = service.compute_stats("draft_approved_1")
        
        assert stats.avg_content_quality == 5.0
        assert stats.avg_usefulness == 3.0
        assert stats.avg_completeness is None
        assert stats.avg_language_quality is None
        # Durchschnitt nur der zwei bewerteten Skalen: (5+3)/2 = 4.0
        assert stats.avg_overall == 4.0


class TestDraftQualityRatingIsolation:
    """Tests für Akten-Isolation der Bewertungen."""
    
    def test_ratings_isolated_per_matter(self, test_data: dict):
        """Bewertungen sind isoliert pro Akte."""
        session = test_data["test_session"]
        
        # Zweite Akte
        matter2 = Matter(
            id="matter2",
            client_id="client1",
            title="Testakte 2",
            reference_number="AZ-2024-002",
        )
        session.add(matter2)
        
        # Entwurf in zweiter Akte
        draft_matter2 = Draft(
            id="draft_matter2_1",
            matter_id="matter2",
            content="Entwurf in anderer Akte",
            status="approved",
        )
        session.add(draft_matter2)
        session.commit()
        
        service = DraftQualityService(session)
        
        # Bewertung für Entwurf aus Akte 1
        service.record_rating(
            draft_id="draft_approved_1",
            rated_by_user_id="attorney1",
            input_data=DraftQualityRatingInput(content_quality=5),
        )
        
        # Bewertung für Entwurf aus Akte 2
        service.record_rating(
            draft_id="draft_matter2_1",
            rated_by_user_id="attorney1",
            input_data=DraftQualityRatingInput(content_quality=2),
        )
        
        # Bewertungen sollten getrennt sein
        ratings_matter1 = service.get_ratings_by_matter("matter1")
        ratings_matter2 = service.get_ratings_by_matter("matter2")
        
        assert len(ratings_matter1) == 1
        assert len(ratings_matter2) == 1
        assert ratings_matter1[0].draft_id == "draft_approved_1"
        assert ratings_matter2[0].draft_id == "draft_matter2_1"
