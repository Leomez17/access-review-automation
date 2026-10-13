"""One test per rule. Remove a @pytest.mark.skip line once you've written that rule."""
import pandas as pd
import pytest

from access_review import rules
from access_review.loader import load_view

REVIEW_DATE = pd.Timestamp("2026-10-12")


@pytest.fixture(scope="module")
def view():
    return load_view()


def flagged(rule, view):
    return {f.grant_id for f in rule(view, REVIEW_DATE)}


def test_join_keeps_every_grant(view):
    assert len(view) == 40


def test_leaver(view):
    assert flagged(rules.rule_leaver, view) == {"G15", "G16", "G26", "G27"}


def test_orphaned_account(view):
    assert flagged(rules.rule_orphaned_account, view) == {"G31", "G32"}


def test_orphaned_ignores_service_and_break_glass(view):
    hits = flagged(rules.rule_orphaned_account, view)
    assert not hits & {"G34", "G35", "G36"}


def test_contract_ended(view):
    assert flagged(rules.rule_contract_ended, view) == {"G22", "G23"}


@pytest.mark.skip(reason="TODO: implement rule_dormant_or_test")
def test_dormant_or_test(view):
    hits = flagged(rules.rule_dormant_or_test, view)
    assert hits == {"G31", "G32", "G37"}
    assert "G17" not in hits  # long-term leave is not dormant
    assert "G36" not in hits  # break-glass is meant to be unused


def test_service_account_risk(view):
    assert flagged(rules.rule_service_account_risk, view) == {"G35"}


def test_shared_account(view):
    assert flagged(rules.rule_shared_account, view) == {"G33"}


@pytest.mark.skip(reason="TODO: implement rule_segregation_of_duties")
def test_segregation_of_duties(view):
    assert flagged(rules.rule_segregation_of_duties, view) == {"G24"}


def test_excessive_privilege(view):
    hits = flagged(rules.rule_excessive_privilege, view)
    assert hits == {"G06", "G20", "G22", "G26"}  # G26 is also a leaver: one grant can break several rules
    assert "G08" not in hits  # named admin account is the right place for Domain Admins


@pytest.mark.skip(reason="TODO: implement rule_standing_admin")
def test_standing_admin(view):
    assert flagged(rules.rule_standing_admin, view) == {"G19"}


@pytest.mark.skip(reason="TODO: implement rule_access_outside_department")
def test_access_outside_department(view):
    assert flagged(rules.rule_access_outside_department, view) == {"G11", "G20", "G24"}
