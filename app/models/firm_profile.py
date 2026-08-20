"""FirmProfile – Kanzleiname, Adresse und Kontaktdaten (20.08.).

Bewusst als SINGLETON gedacht (genau eine Zeile für die gesamte
Installation, siehe app/firm_profile/service.py: get_firm_profile) - anders
als Client/Matter/Document ist das hier keine mandantenbezogene Fachdaten-
Entität, sondern ein einziger, kanzleiweiter Stammdatensatz (Name/Anschrift/
Kontakt der Kanzlei selbst), vergleichbar mit einer Konfiguration. Als
eigenes DB-Modell statt in der .env geführt (anders als z. B. Scan-Ordner/
Mail-Zugangsdaten, siehe app/web/settings_router.py) - Briefkopf-Angaben
sind Anzeigedaten, keine Infrastruktur-/Zugangskonfiguration, gehören daher
nicht in .env/Settings.

Vorgesehener Verwendungszweck (siehe app/export/docx_export_service.py):
liefert Name/Anschrift/Kontakt für den Briefkopf generierter DOCX-
Schriftsätze.

Logo/Unterschrift (20.08., Nachtrag "Briefkopf- und Signatur-Verwaltung"):
`logo_path`/`signature_path` verweisen wie bei `Document.file_path`
(app/models/document.py) auf das Original im Dateisystem - die Bilddatei
selbst wird NICHT in der Datenbank gespeichert. Upload/Validierung/
Speicherort siehe app/web/settings_router.py."""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class FirmProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "firm_profiles"

    firm_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    street: Mapped[str | None] = mapped_column(String(255), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Name unter der Unterschriften-Grafik im DOCX-Export (z. B.
    # "Rechtsanwältin Anna Muster") - bewusst getrennt von `firm_name`:
    # eine Unterschrift gehört zu EINER unterzeichnenden Person, nicht zur
    # Kanzlei als Ganzes.
    signatory_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    logo_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    logo_original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    signature_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    signature_original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Wer die Angaben zuletzt geändert hat (Nachvollziehbarkeit, gleiches
    # Muster wie PromptTemplate.updated_by_actor) - kein volles Audit-Log
    # nötig, da es sich um reine Stammdaten ohne KI-/Freigabebezug handelt.
    updated_by_actor: Mapped[str | None] = mapped_column(String(128), nullable=True)
