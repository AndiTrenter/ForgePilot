"""Unit-Tests für backend.policy_engine."""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from policy_engine import (  # noqa: E402
    evaluate_action,
    is_forbidden,
    needs_approval,
    is_auto_allowed,
    AUTO_ALLOWED,
    APPROVAL_REQUIRED,
    FORBIDDEN,
)


def test_auto_allowed_actions_pass():
    d = evaluate_action("build_app")
    assert d.allowed is True
    assert d.requires_approval is False
    assert d.category == "auto"


def test_approval_required_actions():
    d = evaluate_action("deploy_production")
    assert d.allowed is True
    assert d.requires_approval is True
    assert d.category == "approval"


def test_forbidden_actions_blocked():
    d = evaluate_action("wipe_database")
    assert d.allowed is False
    assert d.requires_approval is False
    assert d.category == "forbidden"


def test_unknown_action_fails_closed():
    d = evaluate_action("some_weird_tool_42")
    # fail-closed: erlaubt, aber Approval erzwingen
    assert d.allowed is True
    assert d.requires_approval is True
    assert d.category == "unknown"


def test_empty_action_blocked():
    d = evaluate_action("")
    assert d.allowed is False
    assert d.category == "forbidden"


def test_helpers_consistent():
    assert is_forbidden("delete_volume") is True
    assert is_auto_allowed("run_tests") is True
    assert needs_approval("db_migration") is True
    assert needs_approval("run_tests") is False


def test_sets_are_disjoint():
    assert AUTO_ALLOWED.isdisjoint(APPROVAL_REQUIRED)
    assert AUTO_ALLOWED.isdisjoint(FORBIDDEN)
    assert APPROVAL_REQUIRED.isdisjoint(FORBIDDEN)


def test_to_dict_shape():
    d = evaluate_action("mark_complete").to_dict()
    assert set(d.keys()) == {"action", "allowed", "requires_approval", "reason", "category"}


def test_whitespace_normalized():
    d = evaluate_action("  build_app  ")
    assert d.category == "auto"
