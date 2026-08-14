"""Tests fuer app/privacy/security_check.py.

Kernanforderung (Architekturvorgabe, wörtlich): "Bei einem nicht
eindeutigen Ergebnis: KEIN API-AUFRUF." - jeder Test, der einen Grund zum
Blockieren simuliert, muss `passed=False` liefern."""

from app.privacy.pseudonymizer import PseudonymMapping, Pseudonymizer
from app.privacy.security_check import ALLOWED_PURPOSES, SecurityCheckService


def _clean_pseudonymized_text() -> tuple[str, list[PseudonymMapping]]:
    p = Pseudonymizer()
    text = "Sehr geehrter Herr Max Mustermann, Az.: 123/24, Frist 15.03.2027."
    return p.pseudonymize(text, known_entities={"mandant": ["Max Mustermann"]})


def test_clean_pseudonymized_text_with_allowed_purpose_passes() -> None:
    text, mappings = _clean_pseudonymized_text()
    checker = SecurityCheckService()

    result = checker.check(text, mappings, purpose="formulate_draft")

    assert result.passed is True
    assert result.reasons == []


def test_disallowed_purpose_blocks_the_call() -> None:
    """Punkt 7: Ist der API-Aufruf für diese Aufgabe zulässig?"""
    text, mappings = _clean_pseudonymized_text()
    checker = SecurityCheckService()

    result = checker.check(text, mappings, purpose="analyze_full_file")

    assert result.passed is False
    assert any("Zweck" in r for r in result.reasons)


def test_all_allowed_purposes_are_text_production_only() -> None:
    """Stichprobenartige Absicherung: die Allowlist darf keine
    Analyse-/Zuordnungs-/Rechercheaufgaben enthalten (Vorgabe Punkt 2)."""
    forbidden_keywords = ["assign", "match", "research", "decide", "send", "analyze"]
    for purpose in ALLOWED_PURPOSES:
        assert not any(keyword in purpose for keyword in forbidden_keywords)


def test_residual_pii_in_supposedly_pseudonymized_text_blocks_the_call() -> None:
    """Punkt 2/3/4: Enthält der Text noch personenbezogene/vertrauliche
    Daten? Simuliert eine unvollständige Pseudonymisierung (E-Mail
    vergessen)."""
    text, mappings = _clean_pseudonymized_text()
    leaky_text = text + " Kontakt: max@example.test"
    checker = SecurityCheckService()

    result = checker.check(leaky_text, mappings, purpose="formulate_draft")

    assert result.passed is False
    assert any("email" in r for r in result.reasons)


def test_missing_placeholder_in_text_blocks_the_call() -> None:
    """Punkt 5: Wurden alle bekannten Platzhalter korrekt gesetzt?
    Simuliert eine Mapping-Text-Inkonsistenz."""
    _, mappings = _clean_pseudonymized_text()
    checker = SecurityCheckService()

    # Text enthaelt die im Mapping erwarteten Platzhalter nicht.
    result = checker.check("Ein völlig anderer Text.", mappings, purpose="formulate_draft")

    assert result.passed is False
    assert any("Platzhalter" in r for r in result.reasons)


def test_possible_unrecognized_name_blocks_the_call() -> None:
    """Punkt 6: Gibt es möglicherweise nicht erkannte personenbezogene
    Daten? Ein echter, nicht als bekannte Entität übergebener Name muss
    zum Blockieren führen."""
    checker = SecurityCheckService()

    result = checker.check(
        "Bitte informieren Sie auch Herrn Peter Müller.", [], purpose="formulate_draft"
    )

    assert result.passed is False
    assert any("Peter Müller" in r for r in result.reasons)


def test_common_german_formal_letter_does_not_trigger_false_positive() -> None:
    """Regressionstest fuer den gefundenen Bug: normale deutsche
    Kanzleibrief-Formulierungen (Grossschreibung von Substantiven/
    Hoeflichkeitsform) duerfen NICHT faelschlich als unbekannter Name
    gewertet werden."""
    sample = (
        "Sehr geehrte Damen und Herren,\n"
        "vielen Dank für Ihr Schreiben. Wir haben die Unterlagen geprüft "
        "und teilen Ihnen mit, dass der Einspruch gegen den Steuerbescheid "
        "form- und fristgerecht eingelegt wurde. Die Finanzbehörde hat "
        "eine Frist gesetzt. Mit freundlichen Grüßen"
    )
    checker = SecurityCheckService()

    result = checker.check(sample, [], purpose="formulate_draft")

    assert result.passed is True
    assert result.reasons == []


def test_multiple_problems_all_reported() -> None:
    """Mehrere gleichzeitige Probleme muessen alle in reasons auftauchen,
    nicht nur der erste gefundene."""
    checker = SecurityCheckService()

    result = checker.check(
        "Kontakt: max@example.test, mit Peter Müller besprochen.",
        [],
        purpose="analyze_full_file",
    )

    assert result.passed is False
    assert len(result.reasons) >= 3  # Zweck + Email-Leak + unbekannter Name


def test_real_pipeline_output_passes_when_correctly_pseudonymized() -> None:
    """Integrationstest: der reale Pseudonymizer-Output (nicht
    handgebaut) muss den Security-Check normalerweise bestehen - sonst
    waere die Pipeline in der Praxis dauerhaft blockiert."""
    p = Pseudonymizer()
    text = (
        "Sehr geehrter Herr Max Mustermann, bezugnehmend auf Ihr Schreiben "
        "vom 01.02.2027 (Az.: 55/27) teilen wir mit, dass die Frist am "
        "15.03.2027 endet. Mit freundlichen Grüßen"
    )
    pseudo_text, mappings = p.pseudonymize(
        text, known_entities={"mandant": ["Max Mustermann"]}
    )
    checker = SecurityCheckService()

    result = checker.check(pseudo_text, mappings, purpose="formulate_draft")

    assert result.passed is True, result.reasons
