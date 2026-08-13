"""Document – Dokument (Scan, PDF, Office-Datei, E-Mail-Anhang ...).

Wichtig (Konzept §7 / Prompt 06): Original, extrahierter Text und
technische Metadaten sind strikt getrennte Felder. `file_path` verweist auf
das Original im Dateisystem - die Datenbank ist nicht die einzige Wahrheit
fuer den Dateiinhalt, sondern fuehrt Beziehungen und Status.
`extracted_text`/`ocr_status` werden hier bereits als Schema vorgesehen,
auch wenn die eigentliche OCR-/Extraktionslogik erst in Prompt 06 entsteht.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Document(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "documents"

    matter_id: Mapped[str | None] = mapped_column(
        ForeignKey("matters.id"), nullable=True, index=True
    )
    message_id: Mapped[str | None] = mapped_column(
        ForeignKey("messages.id"), nullable=True, index=True
    )

    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # Pfad im Dateisystem (Intake-/Ablagebereich) - siehe Aktenstruktur,
    # Konzept §7. Die Datei selbst wird nicht in der Datenbank gespeichert.
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Getrennt vom Original: extrahierter/Ocr-Text, erst ab Prompt 06 befuellt.
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # not_needed / pending / done / failed / unsupported_format - bewusst
    # freier String, kein DB-Enum, da die endgueltige Zustandslogik erst in
    # Prompt 06 vollstaendig entstand und sich noch erweitern kann.
    ocr_status: Mapped[str] = mapped_column(
        String(32), default="not_needed", nullable=False
    )

    matter: Mapped["Matter | None"] = relationship(back_populates="documents")
    message: Mapped["Message | None"] = relationship(back_populates="documents")
