"""DraftDocxExportService – Export EINES Entwurfs als formatierte `.docx`
(Schriftsatz-Generator, 20.08.; Briefkopf-/Signatur-Verwaltung, Nachtrag
20.08.).

Getrennt von `MatterExportService` (app/export/service.py, ZIP-Export der
GESAMTEN Akte für Auskunftsersuchen/Archivierung) - dieser Service liefert
gezielt EIN druckfertiges Word-Dokument für genau eine Entwurfsversion.

Briefkopf/Unterschrift sind bewusst OPTIONAL (`firm_profile=None` oder ein
leerer Datensatz möglich) - solange auf der Kanzlei-Profilseite
(/dashboard/settings/profile, app/web/settings_router.py) kein Kanzleiname
eingetragen wurde, bleibt der Export ohne Briefkopf (ehrlicher als ein
Platzhalter-Absender). Logo/Unterschrift werden UNABHÄNGIG voneinander nur
eingebettet, wenn die jeweilige Datei tatsächlich existiert - ein in der DB
referenzierter, aber inzwischen von der Platte verschwundener Pfad darf den
Export nicht zum Absturz bringen (siehe `_image_exists`).

Layout:
- Kopfbereich (`document.sections[0].header`, erscheint auf JEDER Seite):
  Logo zentriert oben, darunter Kanzleiname (fett) + Anschrift/Kontakt,
  abgeschlossen mit einer dünnen Trennlinie (`_add_bottom_border`).
- Fußbereich/Signatur: bewusst NICHT im Word-„Footer" (der würde auf JEDER
  Seite wiederholt - eine Unterschrift gehört aber einmalig ans Ende des
  Schreibens) - stattdessen als letzter Abschnitt des Dokumentinhalts nach
  dem Entwurfstext: Unterschriften-Grafik, darunter der getippte Name.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from docx import Document as DocxDocument
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

from app.models import Draft, FirmProfile, Matter

DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

_DIVIDER_COLOR = "CBD5E1"  # entspricht --paper-line (#e2e8f0-nah, druckfertig etwas kraeftiger)
_LOGO_HEIGHT_CM = 1.6
_SIGNATURE_HEIGHT_CM = 2.2


def _image_exists(path: str | None) -> bool:
    return bool(path) and Path(path).exists()


def _add_bottom_border(paragraph, *, size: int = 6, space: int = 6) -> None:
    """Fügt dem Absatz eine dünne untere Rahmenlinie hinzu (python-docx hat
    dafür keine High-Level-API - direkte OXML-Manipulation, Standardmuster
    für Word-Absatzrahmen). `size` in 1/8pt (6 = 0.75pt, eine dezente
    Trennlinie statt eines dicken Balkens)."""
    paragraph_format_element = paragraph._p.get_or_add_pPr()
    border_element = OxmlElement("w:pBdr")
    bottom_element = OxmlElement("w:bottom")
    bottom_element.set(qn("w:val"), "single")
    bottom_element.set(qn("w:sz"), str(size))
    bottom_element.set(qn("w:space"), str(space))
    bottom_element.set(qn("w:color"), _DIVIDER_COLOR)
    border_element.append(bottom_element)
    paragraph_format_element.append(border_element)


class DraftDocxExportService:
    def export_draft(
        self, draft: Draft, matter: Matter, firm_profile: FirmProfile | None = None
    ) -> BytesIO:
        document = DocxDocument()

        style = document.styles["Normal"]
        style.font.name = "Calibri"
        style.font.size = Pt(11)

        has_letterhead_content = firm_profile is not None and (
            firm_profile.firm_name.strip() or _image_exists(firm_profile.logo_path)
        )
        if has_letterhead_content:
            self._build_header(document, firm_profile)

        document.add_heading(matter.title or "Schriftsatz", level=1)
        meta = document.add_paragraph()
        meta.add_run(
            f"Entwurf Version {draft.version} · Stand "
            f"{draft.updated_at.strftime('%d.%m.%Y')}"
        ).italic = True

        # Leerzeilen als Absatzgrenzen - der Entwurfstext selbst ist reiner
        # Fließtext ohne eigene Formatierungssyntax (siehe Draft.content).
        for block in draft.content.split("\n\n"):
            block = block.strip()
            if block:
                document.add_paragraph(block)

        if firm_profile is not None and (
            _image_exists(firm_profile.signature_path)
            or (firm_profile.signatory_name or "").strip()
        ):
            self._add_signature_block(document, firm_profile)

        buffer = BytesIO()
        document.save(buffer)
        buffer.seek(0)
        return buffer

    def _build_header(self, document: DocxDocument, firm_profile: FirmProfile) -> None:
        """Seiten-Kopfbereich: Logo (falls vorhanden) zentriert oben,
        darunter Kanzleiname/Anschrift/Kontakt, abgeschlossen mit einer
        Trennlinie. Läuft auf JEDER Seite des Dokuments (echter Word-
        Header, nicht nur ein vorangestellter Body-Absatz)."""
        header = document.sections[0].header
        header.is_linked_to_previous = False

        # Der frische Header hat bereits einen leeren Absatz - wiederverwenden
        # statt einen weiteren leeren voranzustellen.
        paragraphs_used = 0
        if _image_exists(firm_profile.logo_path):
            logo_paragraph = header.paragraphs[0]
            logo_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            logo_paragraph.add_run().add_picture(
                firm_profile.logo_path, height=Cm(_LOGO_HEIGHT_CM)
            )
            paragraphs_used += 1

        firm_name = firm_profile.firm_name.strip()
        if firm_name:
            name_paragraph = (
                header.add_paragraph() if paragraphs_used else header.paragraphs[0]
            )
            name_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            name_run = name_paragraph.add_run(firm_name)
            name_run.bold = True
            name_run.font.size = Pt(12)
            paragraphs_used += 1

        detail_lines = self._address_and_contact_lines(firm_profile)
        last_paragraph = None
        for line in detail_lines:
            detail_paragraph = (
                header.add_paragraph() if paragraphs_used else header.paragraphs[0]
            )
            detail_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            detail_run = detail_paragraph.add_run(line)
            detail_run.font.size = Pt(9)
            paragraphs_used += 1
            last_paragraph = detail_paragraph

        # Trennlinie unter dem letzten tatsächlich befüllten Absatz - fällt
        # keiner der obigen Zweige zu (nur Logo, kein Text), landet sie
        # unter dem Logo-Absatz.
        _add_bottom_border(last_paragraph or header.paragraphs[0])

    def _address_and_contact_lines(self, firm_profile: FirmProfile) -> list[str]:
        address_line = ", ".join(
            part
            for part in (
                firm_profile.street,
                " ".join(
                    p for p in (firm_profile.postal_code, firm_profile.city) if p
                )
                or None,
            )
            if part
        )
        contact_line = " · ".join(
            part
            for part in (firm_profile.phone, firm_profile.email, firm_profile.website)
            if part
        )
        return [line for line in (address_line, contact_line) if line]

    def _add_signature_block(self, document: DocxDocument, firm_profile: FirmProfile) -> None:
        """Unterschriften-Grafik + getippter Name als letzter Abschnitt des
        Dokumentinhalts (siehe Moduldocstring, warum bewusst NICHT im
        Word-Footer)."""
        document.add_paragraph()  # Abstand zum Brieftext

        if _image_exists(firm_profile.signature_path):
            signature_paragraph = document.add_paragraph()
            signature_paragraph.add_run().add_picture(
                firm_profile.signature_path, height=Cm(_SIGNATURE_HEIGHT_CM)
            )

        signatory_name = (firm_profile.signatory_name or "").strip()
        if signatory_name:
            name_paragraph = document.add_paragraph()
            name_paragraph.add_run(signatory_name)
