"""Tests for lock mode / type explanations."""

from mydba_tui.renderers.table import explain_lock_mode


def test_innodb_single_component() -> None:
    assert explain_lock_mode("X") == "Exclusive"
    assert explain_lock_mode("S") == "Shared"
    assert explain_lock_mode("IX") == "Intention Exclusive"
    assert explain_lock_mode("IS") == "Intention Shared"


def test_innodb_compound_components() -> None:
    assert explain_lock_mode("X,REC_NOT_GAP") == "Exclusive, record only (no gap)"
    assert explain_lock_mode("S,GAP") == "Shared, gap lock"


def test_mdl_types() -> None:
    assert explain_lock_mode("SHARED_READ") == "Shared Read"
    assert explain_lock_mode("EXCLUSIVE") == "Exclusive"
    assert explain_lock_mode("INTENTION_EXCLUSIVE") == "Intention Exclusive"


def test_unknown_token_passthrough() -> None:
    """Unknown tokens are passed through unchanged, never hidden."""
    assert explain_lock_mode("WEIRD_MODE") == "WEIRD_MODE"


def test_empty() -> None:
    assert explain_lock_mode("") == ""
    assert explain_lock_mode("   ") == ""
