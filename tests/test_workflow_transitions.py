"""Tests fuer app/workflow/transitions.py (Prompt 20)."""

from app.models.workflow_run import VALID_WORKFLOW_STATUSES
from app.workflow.transitions import ALLOWED_TRANSITIONS


def test_all_valid_statuses_have_a_transition_entry() -> None:
    assert set(ALLOWED_TRANSITIONS.keys()) == set(VALID_WORKFLOW_STATUSES)


def test_archived_is_terminal() -> None:
    assert ALLOWED_TRANSITIONS["ARCHIVED"] == set()


def test_error_reachable_from_every_non_terminal_state() -> None:
    for status, targets in ALLOWED_TRANSITIONS.items():
        if status in ("ARCHIVED", "ERROR"):
            continue
        assert "ERROR" in targets, f"{status} kann ERROR nicht erreichen"


def test_error_can_recover_to_processing() -> None:
    assert "PROCESSING" in ALLOWED_TRANSITIONS["ERROR"]
