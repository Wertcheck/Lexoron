"""Fallszenario-Vorlagen (Prompt 29).

Jedes Szenario beschreibt einen realistischen, aber VOLLSTÄNDIG
FIKTIVEN steuerrechtlichen Fall - orientiert an den bereits im Projekt
verwendeten Dokumenttypen (`ALLOWED_DOCUMENT_TYPES`,
app/classification/schema.py) und Rechtsquellentypen (Prompt 14).

GRUNDREGEL (Konzept-Annahme A3, ARCHITECTURE.md §9, durchgängig im
gesamten Projekt eingehalten): AUSSCHLIESSLICH synthetische Daten - keine
echten Namen, keine echten Mandanten, keine echten Aktenzeichen. Alle
Namen sind deutsche Standard-Platzhandernamen ("Max Mustermann" u. Ä.,
das deutsche Äquivalent zu "John Doe") oder klar erfundene
Firmennamen-Muster. E-Mail-Adressen nutzen ausschließlich
`.invalid`/`.test`-Domains (RFC 2606) - technisch garantiert nicht
zustellbar, können also nie versehentlich eine echte Person erreichen.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CaseScenario:
    key: str
    matter_title_template: str
    practice_area: str
    email_subject_template: str
    email_body_template: str
    document_filename_template: str
    document_extracted_text_template: str
    classified_type: str
    has_deadline: bool
    deadline_days_from_now: int | None
    deadline_source_text_template: str | None


SCENARIOS: tuple[CaseScenario, ...] = (
    CaseScenario(
        key="einspruch_steuerbescheid",
        matter_title_template="Einspruch Steuerbescheid {jahr} – {mandant_kurz}",
        practice_area="Einkommensteuer",
        email_subject_template="Steuerbescheid {jahr} erhalten – bitte um Prüfung",
        email_body_template=(
            "Sehr geehrte Damen und Herren,\n\n"
            "anbei erhalten Sie den Steuerbescheid für das Jahr {jahr}. Ich bitte um "
            "Prüfung, insbesondere hinsichtlich der Werbungskosten in Zeile 14, die "
            "meines Erachtens nicht vollständig berücksichtigt wurden.\n\n"
            "Mit freundlichen Grüßen\n{mandant}"
        ),
        document_filename_template="steuerbescheid_{jahr}_{mandant_kurz}.pdf",
        document_extracted_text_template=(
            "Bescheid für {jahr} über Einkommensteuer und Solidaritätszuschlag.\n"
            "Festgesetzte Einkommensteuer: {betrag} EUR.\n"
            "Werbungskosten wurden pauschal mit 1.230 EUR angesetzt.\n"
            "Rechtsbehelfsbelehrung: Einspruch innerhalb eines Monats nach Bekanntgabe."
        ),
        classified_type="Sonstiges",
        has_deadline=True,
        deadline_days_from_now=28,
        deadline_source_text_template=(
            "Einspruch ist innerhalb eines Monats nach Bekanntgabe des Bescheids "
            "vom {bescheid_datum} einzulegen."
        ),
    ),
    CaseScenario(
        key="betriebspruefung",
        matter_title_template="Betriebsprüfung {jahr} – {mandant_kurz}",
        practice_area="Betriebsprüfung",
        email_subject_template="Ankündigung einer Betriebsprüfung",
        email_body_template=(
            "Sehr geehrte Damen und Herren,\n\n"
            "das Finanzamt hat für unser Unternehmen eine Betriebsprüfung für die "
            "Jahre {jahr_von} bis {jahr} angekündigt. Der Prüfungsbeginn ist für den "
            "{pruefungsbeginn} vorgesehen. Könnten Sie uns dabei unterstützen und "
            "begleiten?\n\n"
            "Mit freundlichen Grüßen\n{mandant}"
        ),
        document_filename_template="pruefungsanordnung_{mandant_kurz}.pdf",
        document_extracted_text_template=(
            "Prüfungsanordnung gemäß § 196 AO.\n"
            "Prüfungszeitraum: {jahr_von} bis {jahr}.\n"
            "Prüfungsbeginn: {pruefungsbeginn}.\n"
            "Zu prüfende Steuerarten: Körperschaftsteuer, Gewerbesteuer, Umsatzsteuer."
        ),
        classified_type="Gerichtliches Schreiben",
        has_deadline=False,
        deadline_days_from_now=None,
        deadline_source_text_template=None,
    ),
    CaseScenario(
        key="umsatzsteuer_nachschau",
        matter_title_template="Umsatzsteuer-Nachschau – {mandant_kurz}",
        practice_area="Umsatzsteuer",
        email_subject_template="Unterlagen zur Umsatzsteuer-Nachschau",
        email_body_template=(
            "Sehr geehrte Damen und Herren,\n\n"
            "anbei die angeforderten Unterlagen zur Umsatzsteuer-Nachschau, wie "
            "telefonisch besprochen. Bitte prüfen Sie, ob die Vorsteuerabzüge korrekt "
            "dokumentiert sind.\n\n"
            "Mit freundlichen Grüßen\n{mandant}"
        ),
        document_filename_template="ust_unterlagen_{mandant_kurz}.pdf",
        document_extracted_text_template=(
            "Zusammenstellung der Vorsteuerabzüge für den Zeitraum {jahr}.\n"
            "Summe Vorsteuer: {betrag} EUR.\n"
            "Belege liegen für alle Positionen vor."
        ),
        classified_type="Sonstiges",
        has_deadline=False,
        deadline_days_from_now=None,
        deadline_source_text_template=None,
    ),
    CaseScenario(
        key="mahnung_zahlungsverzug",
        matter_title_template="Mahnung Zahlungsverzug – {mandant_kurz}",
        practice_area="Forderungsmanagement",
        email_subject_template="Mahnung erhalten – bitte um Prüfung",
        email_body_template=(
            "Sehr geehrte Damen und Herren,\n\n"
            "ich habe die beigefügte Mahnung erhalten und halte die Forderung für "
            "nicht berechtigt, da die zugrunde liegende Leistung nicht vollständig "
            "erbracht wurde. Ich bitte um rechtliche Einschätzung.\n\n"
            "Mit freundlichen Grüßen\n{mandant}"
        ),
        document_filename_template="mahnung_{mandant_kurz}.pdf",
        document_extracted_text_template=(
            "Mahnung wegen Zahlungsverzugs.\n"
            "Offener Betrag: {betrag} EUR zzgl. Verzugszinsen.\n"
            "Zahlungsfrist: 14 Tage ab Zugang dieses Schreibens."
        ),
        classified_type="Mahnung",
        has_deadline=True,
        deadline_days_from_now=14,
        deadline_source_text_template="Zahlungsfrist: 14 Tage ab Zugang dieses Schreibens.",
    ),
    CaseScenario(
        key="vertragspruefung",
        matter_title_template="Vertragsprüfung – {mandant_kurz}",
        practice_area="Vertragsrecht",
        email_subject_template="Bitte um Prüfung eines Vertragsentwurfs",
        email_body_template=(
            "Sehr geehrte Damen und Herren,\n\n"
            "anbei ein Vertragsentwurf, den ich vor Unterzeichnung gerne rechtlich "
            "geprüft haben möchte, insbesondere die Haftungsklausel in § 8.\n\n"
            "Mit freundlichen Grüßen\n{mandant}"
        ),
        document_filename_template="vertragsentwurf_{mandant_kurz}.pdf",
        document_extracted_text_template=(
            "Vertragsentwurf zwischen den Parteien.\n"
            "§ 8 Haftung: Die Haftung wird auf Vorsatz und grobe Fahrlässigkeit "
            "beschränkt.\n"
            "Laufzeit: 24 Monate, Kündigungsfrist 3 Monate zum Laufzeitende."
        ),
        classified_type="Vertrag",
        has_deadline=False,
        deadline_days_from_now=None,
        deadline_source_text_template=None,
    ),
    CaseScenario(
        key="kuendigung_widerspruch",
        matter_title_template="Widerspruch Kündigung – {mandant_kurz}",
        practice_area="Arbeitsrecht",
        email_subject_template="Kündigung erhalten – Widerspruch prüfen",
        email_body_template=(
            "Sehr geehrte Damen und Herren,\n\n"
            "mir wurde fristlos gekündigt, obwohl ich die vorgeworfenen Pflichtverletzungen "
            "bestreite. Ich möchte gerne Widerspruch einlegen und bitte um Ihre Einschätzung "
            "der Erfolgsaussichten.\n\n"
            "Mit freundlichen Grüßen\n{mandant}"
        ),
        document_filename_template="kuendigung_{mandant_kurz}.pdf",
        document_extracted_text_template=(
            "Fristlose Kündigung des Arbeitsverhältnisses zum {bescheid_datum}.\n"
            "Begründung: Wiederholte Verletzung arbeitsvertraglicher Pflichten.\n"
            "Hinweis auf Klagefrist von drei Wochen (§ 4 KSchG)."
        ),
        classified_type="Kündigungsschreiben",
        has_deadline=True,
        deadline_days_from_now=21,
        deadline_source_text_template=(
            "Klagefrist von drei Wochen nach Zugang der Kündigung (§ 4 KSchG)."
        ),
    ),
)
