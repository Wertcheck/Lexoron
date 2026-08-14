"""Tests fuer app/privacy/gateway.py.

Schwerpunkt: die kritische Eigenschaft, dass derselbe Name ueber mehrere
Payload-Felder hinweg IMMER denselben Platzhalter erhaelt (siehe
Moduldocstring in gateway.py fuer die Begruendung)."""

from app.privacy.gateway import ClaudePrivacyGateway


def test_allowed_request_produces_pseudonymized_payload() -> None:
    gw = ClaudePrivacyGateway()

    result = gw.prepare_request(
        purpose="formulate_draft",
        sachverhalt="Mandant Max Mustermann wendet sich gegen den Steuerbescheid.",
        known_entities={"mandant": ["Max Mustermann"]},
    )

    assert result.allowed is True
    assert result.payload is not None
    assert "Max Mustermann" not in result.payload.anonymisierter_sachverhalt
    assert "[MANDANT_01]" in result.payload.anonymisierter_sachverhalt


def test_same_entity_gets_same_placeholder_across_fields() -> None:
    """Kernanforderung: Konsistenz ueber Feldgrenzen hinweg."""
    gw = ClaudePrivacyGateway()

    result = gw.prepare_request(
        purpose="formulate_draft",
        sachverhalt="Mandant Max Mustermann hat Einspruch eingelegt.",
        argumentationspunkte=["Max Mustermann handelte fristgerecht."],
        known_entities={"mandant": ["Max Mustermann"]},
    )

    assert result.allowed is True
    assert "[MANDANT_01]" in result.payload.anonymisierter_sachverhalt
    assert "[MANDANT_01]" in result.payload.anonymisierte_argumentationspunkte[0]
    # Nur EIN Mapping-Eintrag fuer den Wert, nicht zwei verschiedene.
    mandant_mappings = [m for m in result.mappings if m.category == "mandant"]
    assert len(mandant_mappings) == 1


def test_different_entities_in_different_fields_get_different_placeholders() -> None:
    gw = ClaudePrivacyGateway()

    result = gw.prepare_request(
        purpose="formulate_draft",
        sachverhalt="Mandant Max Mustermann.",
        argumentationspunkte=["Die Gegenseite Erika Musterfrau bestreitet dies."],
        known_entities={"mandant": ["Max Mustermann"], "gegner": ["Erika Musterfrau"]},
    )

    assert "[MANDANT_01]" in result.payload.anonymisierter_sachverhalt
    assert "[GEGNER_01]" in result.payload.anonymisierte_argumentationspunkte[0]


def test_unrecognized_pii_blocks_request_and_produces_no_payload() -> None:
    gw = ClaudePrivacyGateway()

    result = gw.prepare_request(
        purpose="formulate_draft",
        sachverhalt="Bitte informieren Sie auch Herrn Peter Müller.",
    )

    assert result.allowed is False
    assert result.payload is None
    assert len(result.reasons) > 0


def test_disallowed_purpose_blocks_request() -> None:
    gw = ClaudePrivacyGateway()

    result = gw.prepare_request(purpose="analyze_full_file", sachverhalt="Ein Text.")

    assert result.allowed is False
    assert result.payload is None


def test_reconstruct_response_restores_original_values() -> None:
    gw = ClaudePrivacyGateway()
    result = gw.prepare_request(
        purpose="formulate_draft",
        sachverhalt="Mandant Max Mustermann.",
        known_entities={"mandant": ["Max Mustermann"]},
    )
    assert result.allowed is True

    claude_response = "Sehr geehrter Herr [MANDANT_01], wir bestätigen den Eingang."

    reconstructed = gw.reconstruct_response(claude_response, result.mappings)

    assert reconstructed == "Sehr geehrter Herr Max Mustermann, wir bestätigen den Eingang."
    assert "[MANDANT_01]" not in reconstructed


def test_multiple_argumente_and_quellen_are_correctly_split() -> None:
    gw = ClaudePrivacyGateway()

    result = gw.prepare_request(
        purpose="formulate_draft",
        sachverhalt="Sachverhalt ohne PII.",
        argumentationspunkte=["Erster Punkt.", "Zweiter Punkt.", "Dritter Punkt."],
        quellenverweise=["§ 355 AO.", "§ 356 AO."],
    )

    assert result.allowed is True
    assert result.payload.anonymisierte_argumentationspunkte == [
        "Erster Punkt.",
        "Zweiter Punkt.",
        "Dritter Punkt.",
    ]
    assert result.payload.anonymisierte_quellenverweise == ["§ 355 AO.", "§ 356 AO."]


def test_empty_argumente_and_quellen_produce_empty_lists() -> None:
    gw = ClaudePrivacyGateway()

    result = gw.prepare_request(purpose="formulate_draft", sachverhalt="Nur Sachverhalt.")

    assert result.allowed is True
    assert result.payload.anonymisierte_argumentationspunkte == []
    assert result.payload.anonymisierte_quellenverweise == []


def test_missing_vorlage_results_in_none() -> None:
    gw = ClaudePrivacyGateway()

    result = gw.prepare_request(purpose="formulate_draft", sachverhalt="Text ohne Vorlage.")

    assert result.allowed is True
    assert result.payload.schreibvorlage is None


def test_vorlage_is_preserved_when_provided() -> None:
    gw = ClaudePrivacyGateway()

    result = gw.prepare_request(
        purpose="formulate_draft",
        sachverhalt="Text.",
        vorlage="Sehr geehrte Damen und Herren,",
    )

    assert result.allowed is True
    assert result.payload.schreibvorlage == "Sehr geehrte Damen und Herren,"


def test_injection_attempt_with_internal_markers_does_not_break_parsing() -> None:
    """Ein Text, der zufällig/absichtlich die internen Trennmarkierungen
    enthält, darf die Feldaufteilung nicht durcheinanderbringen."""
    gw = ClaudePrivacyGateway()

    result = gw.prepare_request(
        purpose="formulate_draft",
        sachverhalt="Text mit @@GATEWAY_VORLAGE@@ eingebettetem Marker.",
    )

    assert result.allowed is True
    assert "@@GATEWAY_VORLAGE@@" not in result.payload.anonymisierter_sachverhalt
    assert result.payload.schreibvorlage is None  # nicht faelschlich befuellt


def test_gateway_result_has_correct_purpose_even_when_blocked() -> None:
    gw = ClaudePrivacyGateway()

    result = gw.prepare_request(purpose="analyze_full_file", sachverhalt="Text.")

    assert result.purpose == "analyze_full_file"


def test_style_field_passed_through_without_pseudonymization() -> None:
    """Der Stilwunsch selbst enthaelt typischerweise keine PII und muss
    unveraendert ankommen."""
    gw = ClaudePrivacyGateway()

    result = gw.prepare_request(
        purpose="formulate_draft", sachverhalt="Text.", stil="förmlich, sachlich"
    )

    assert result.payload.gewuenschter_stil == "förmlich, sachlich"
