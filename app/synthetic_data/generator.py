"""SyntheticDataGenerator – erzeugt realistische, vollständig fiktive
Testfälle (Prompt 29).

Zweck: Demo-/Entwicklungsdaten für das Dashboard OHNE echte
Mandantendaten (Konzept-Annahme A3, siehe app/synthetic_data/scenarios.py
für die Grundregel) UND die Datengrundlage für den in Prompt 30
geforderten Qualitäts-Benchmark ("≥20 synthetische Fälle") - dieser
Generator liefert die Fälle, Prompt 30 baut die Bewertungslogik darauf
auf. Bewusst hier NICHT vermischt (eigene Zuständigkeit).

Deterministisch bei gesetztem `seed` - wichtig für einen reproduzierbaren
Benchmark (Prompt 30): derselbe Seed erzeugt exakt dieselben Fälle, ein
Qualitätsvergleich zwischen zwei Codeständen bleibt dadurch fair.

Erzeugt AUSSCHLIESSLICH lokale Datenbankzeilen - ruft an KEINER Stelle
die Claude API auf (kein Kostenrisiko, kein Netzwerkzugriff nötig).
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models import (
    AuditEvent,
    Client,
    Deadline,
    Document,
    KnowledgeItem,
    Matter,
    Message,
    Source,
)
from app.synthetic_data.scenarios import SCENARIOS, CaseScenario

# Deutsche Standard-Platzhalternamen (das Äquivalent zu "John Doe") -
# bewusst KEINE echten Personen, auch keine entfernt realen Personen
# nachempfundenen Namen. Reine Vor-/Nachname-Kombinatorik erzeugt genug
# Varianz für >20 Fälle, ohne eine Namensliste "voller" Personen zu
# brauchen.
_VORNAMEN = (
    "Max", "Erika", "Thomas", "Sabine", "Michael", "Petra", "Andreas", "Julia",
    "Stefan", "Claudia", "Martin", "Nicole", "Frank", "Sandra", "Christian", "Anna",
)
_NACHNAMEN = (
    "Mustermann", "Musterfrau", "Beispiel", "Schmidt", "Meier", "Fischer",
    "Weber", "Wagner", "Becker", "Hoffmann", "Schulz", "Neumann",
)
_FIRMENNAMEN_MUSTER = (
    "Musterbau GmbH", "Beispiel Consulting AG", "Handwerk Schmidt & Söhne",
    "Testhandel Weber KG", "Musterhandwerk Fischer GmbH", "Beispiel Logistik GmbH",
)


@dataclass
class SyntheticCase:
    """Bündelt alle für einen Fall erzeugten Datensätze - erleichtert
    Tests/Auswertungen (Prompt 30), die auf mehrere Teile gleichzeitig
    zugreifen wollen."""

    client: Client
    matter: Matter
    message: Message
    document: Document
    deadline: Deadline | None
    scenario_key: str


class SyntheticDataGenerator:
    def __init__(self, seed: int | None = None) -> None:
        # `seed=None` => nicht-deterministisch (für Demo-Zwecke gedacht,
        # jedes Mal neue Fälle). Ein gesetzter Seed => reproduzierbar
        # (für den Benchmark aus Prompt 30 wichtig).
        self._random = random.Random(seed)

    def _pick_person_name(self) -> str:
        return f"{self._random.choice(_VORNAMEN)} {self._random.choice(_NACHNAMEN)}"

    def _pick_client_name(self) -> str:
        # Mischung aus Privatpersonen und fiktiven Firmen - realistisch
        # für eine Steuerkanzlei mit gemischter Mandantschaft.
        if self._random.random() < 0.5:
            return self._pick_person_name()
        return self._random.choice(_FIRMENNAMEN_MUSTER)

    def _short_name(self, full_name: str) -> str:
        return full_name.split()[0].lower()

    def _email_for(self, name: str) -> str:
        slug = name.lower().replace(" ", ".").replace("&", "und")
        slug = "".join(ch for ch in slug if ch.isalnum() or ch == ".")
        return f"{slug}@example-testdomain.invalid"

    def generate_case(
        self, db: Session, *, scenario_key: str | None = None
    ) -> SyntheticCase:
        """Erzeugt EINEN vollständigen, in sich konsistenten Fall
        (Mandant + Akte + eingehende Nachricht + Dokument + ggf. Frist)
        und committet ihn."""
        scenario = self._pick_scenario(scenario_key)

        mandant_name = self._pick_client_name()
        mandant_kurz = self._short_name(mandant_name)
        jahr = self._random.randint(2022, 2025)
        betrag = self._random.randint(500, 25000)
        bescheid_datum = date.today() - timedelta(days=self._random.randint(1, 10))

        format_kwargs = {
            "mandant": mandant_name,
            "mandant_kurz": mandant_kurz,
            "jahr": jahr,
            "jahr_von": jahr - 2,
            "betrag": f"{betrag:,}".replace(",", "."),
            "bescheid_datum": bescheid_datum.strftime("%d.%m.%Y"),
            "pruefungsbeginn": (
                date.today() + timedelta(days=self._random.randint(10, 40))
            ).strftime("%d.%m.%Y"),
        }

        client = Client(name=mandant_name)
        db.add(client)
        db.flush()

        matter = Matter(
            client_id=client.id,
            title=scenario.matter_title_template.format(**format_kwargs),
            practice_area=scenario.practice_area,
            reference_number=self._generate_unique_reference_number(jahr, db),
        )
        db.add(matter)
        db.flush()

        received_at = datetime.now(timezone.utc) - timedelta(
            days=self._random.randint(0, 5), hours=self._random.randint(0, 23)
        )
        message = Message(
            matter_id=matter.id,
            direction="inbound",
            sender=self._email_for(mandant_name),
            subject=scenario.email_subject_template.format(**format_kwargs),
            body_text=scenario.email_body_template.format(**format_kwargs),
            created_at=received_at,
        )
        db.add(message)
        db.flush()

        filename = scenario.document_filename_template.format(**format_kwargs)
        document = Document(
            matter_id=matter.id,
            message_id=message.id,
            original_filename=filename,
            file_path=f"/data/synthetic/{matter.id}/{filename}",
            extracted_text=scenario.document_extracted_text_template.format(**format_kwargs),
            classified_type=scenario.classified_type,
            classification_confidence=round(self._random.uniform(0.6, 0.95), 2),
        )
        db.add(document)
        db.flush()

        deadline: Deadline | None = None
        if scenario.has_deadline and scenario.deadline_days_from_now is not None:
            source_text = (
                scenario.deadline_source_text_template.format(**format_kwargs)
                if scenario.deadline_source_text_template
                else None
            )
            deadline = Deadline(
                matter_id=matter.id,
                document_id=document.id,
                source_text=source_text,
                due_date=date.today() + timedelta(days=scenario.deadline_days_from_now),
                confidence=round(self._random.uniform(0.5, 0.9), 2),
            )
            db.add(deadline)
            db.flush()

        db.add(
            AuditEvent(
                entity_type="Matter",
                entity_id=matter.id,
                event_type="synthetic_case_generated",
                actor="system",
                details=f"Synthetischer Testfall erzeugt (Szenario: {scenario.key})",
            )
        )
        db.commit()
        db.refresh(client)
        db.refresh(matter)
        db.refresh(message)
        db.refresh(document)
        if deadline is not None:
            db.refresh(deadline)

        return SyntheticCase(
            client=client,
            matter=matter,
            message=message,
            document=document,
            deadline=deadline,
            scenario_key=scenario.key,
        )

    def generate_many(self, db: Session, count: int) -> list[SyntheticCase]:
        """Erzeugt `count` Fälle, zyklisch über alle Szenarien verteilt
        (nicht rein zufällig) - garantiert, dass bei count >= Anzahl
        Szenarien JEDES Szenario mindestens einmal vorkommt (wichtig für
        einen aussagekräftigen Benchmark in Prompt 30)."""
        cases: list[SyntheticCase] = []
        for i in range(count):
            scenario_key = SCENARIOS[i % len(SCENARIOS)].key
            cases.append(self.generate_case(db, scenario_key=scenario_key))
        return cases

    def _pick_scenario(self, scenario_key: str | None) -> CaseScenario:
        if scenario_key is None:
            return self._random.choice(SCENARIOS)
        for scenario in SCENARIOS:
            if scenario.key == scenario_key:
                return scenario
        raise ValueError(
            f"Unbekanntes Szenario '{scenario_key}' - verfügbar: "
            f"{[s.key for s in SCENARIOS]}"
        )

    def _generate_unique_reference_number(self, jahr: int, db: Session) -> str:
        """`Matter.reference_number` trägt eine UNIQUE-Constraint - bei
        wiederholter Generatornutzung gegen dieselbe (Demo-)Datenbank
        könnte der Zufallsraum gelegentlich kollidieren. Prüft daher
        aktiv gegen die DB und generiert bei einem Treffer neu, statt
        einen harten IntegrityError zu riskieren."""
        for _ in range(50):
            laufnummer = self._random.randint(1, 999)
            suffix = self._random.choice(["ESt", "BP", "USt", "Sonst"])
            candidate = f"{jahr}/{laufnummer:04d}-{suffix}"
            exists = (
                db.query(Matter).filter_by(reference_number=candidate).first()
                is not None
            )
            if not exists:
                return candidate
        # Praktisch nie erreicht (Zufallsraum >> realistische Fallzahlen),
        # aber ein garantiert eindeutiger Fallback statt einer Endlosschleife.
        return f"{jahr}/{self._random.randint(1000, 999999)}-Sonst"

    def generate_shared_knowledge_base(
        self, db: Session
    ) -> tuple[list[Source], list[KnowledgeItem]]:
        """Erzeugt eine kleine, freigegebene Rechtsquellen-/Kanzlei-
        Wissensbasis, die für ALLE Fälle gemeinsam genutzt wird
        (realistisch: eine Kanzlei-Wissensbasis ist nicht pro Akte
        getrennt). Nutzt bewusst ECHTE, öffentlich bekannte
        Gesetzesnummern (§ 355 AO usw.) - das sind allgemein bekannte
        Rechtsnormen, keine Mandantendaten, und machen die Fälle
        realistisch nutzbar mit der bestehenden Recherche-/Zitierlogik."""
        sources = [
            Source(
                title="Einspruch gegen Steuerbescheide – Frist",
                source_type="Gesetz",
                reference="§ 355 AO",
                approval_level="freigegeben",
                notes="Einspruchsfrist: ein Monat nach Bekanntgabe des Verwaltungsakts.",
            ),
            Source(
                title="Prüfungsanordnung – Voraussetzungen",
                source_type="Gesetz",
                reference="§ 196 AO",
                approval_level="freigegeben",
                notes="Regelt die formellen Voraussetzungen einer Betriebsprüfung.",
            ),
            Source(
                title="Kündigungsschutzklage – Klagefrist",
                source_type="Gesetz",
                reference="§ 4 KSchG",
                approval_level="freigegeben",
                notes="Klage muss innerhalb von drei Wochen nach Zugang erhoben werden.",
            ),
        ]
        db.add_all(sources)

        knowledge_items = [
            KnowledgeItem(
                title="Standard-Textbaustein: Einspruchseinlegung",
                content=(
                    "Namens und im Auftrag unseres Mandanten legen wir hiermit form- "
                    "und fristgerecht Einspruch gegen den Bescheid vom [DATUM] ein."
                ),
                category="Textbaustein",
                practice_area="Einkommensteuer",
                approval_status="approved",
            ),
            KnowledgeItem(
                title="Standard-Textbaustein: Fristverlängerung beantragen",
                content=(
                    "Wir bitten um Verlängerung der Frist zur Stellungnahme um vier "
                    "Wochen, da uns die vollständigen Unterlagen noch nicht vorliegen."
                ),
                category="Textbaustein",
                practice_area=None,
                approval_status="approved",
            ),
        ]
        db.add_all(knowledge_items)
        db.commit()
        for source in sources:
            db.refresh(source)
        for item in knowledge_items:
            db.refresh(item)
        return sources, knowledge_items
