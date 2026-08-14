"""Tests fuer app/drafting/schema.py (Prompt 17)."""

from app.drafting.schema import DraftingResult, KnowledgeItemReference, SourceReference


def test_default_result_has_empty_lists() -> None:
    result = DraftingResult(success=False)
    assert result.source_list == []
    assert result.knowledge_items_used == []
    assert result.open_review_points == []
    assert result.uncertainties == []
    assert result.blocked_reasons == []


def test_successful_result_with_all_fields() -> None:
    result = DraftingResult(
        success=True,
        draft_id="draft-1",
        draft_text="Sehr geehrte Damen und Herren,",
        source_list=[
            SourceReference(source_id="s1", title="§ 355 AO", reference="§ 355 AO")
        ],
        knowledge_items_used=[
            KnowledgeItemReference(knowledge_item_id="k1", title="Baustein")
        ],
        open_review_points=["Prüfpunkt X"],
        uncertainties=["Unsicherheit Y"],
    )

    assert result.draft_id == "draft-1"
    assert result.source_list[0].reference == "§ 355 AO"
    assert result.knowledge_items_used[0].title == "Baustein"
