"""Access review rules.

Each rule takes the joined review view (see loader.load_view) and the review
date, and returns a list of Finding objects, one per grant it flags.

Two rules are written for you as worked examples: rule_leaver and
rule_orphaned_account. The others are yours to implement. Each has a hint,
and a matching test in tests/test_rules.py that is skipped until you remove
its @pytest.mark.skip line.
"""
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class Finding:
    grant_id: str
    account: str
    category: str
    detail: str


def _findings(rows: pd.DataFrame, category: str, detail_fn) -> list[Finding]:
    return [
        Finding(r.grant_id, r.account, category, detail_fn(r))
        for r in rows.itertuples(index=False)
    ]


# --- Worked examples ------------------------------------------------------

def rule_leaver(view: pd.DataFrame, review_date: pd.Timestamp) -> list[Finding]:
    """HR says the person has left, but their account is still enabled."""
    hits = view[(view["status"] == "Leaver") & (view["enabled"] == "yes")]
    return _findings(
        hits,
        "Leaver",
        lambda r: f"{r.name} left on {r.end_date:%d/%m/%Y} but {r.account} is still enabled",
    )


def rule_orphaned_account(view: pd.DataFrame, review_date: pd.Timestamp) -> list[Finding]:
    """A personal account (user or admin) with no matching HR record."""
    personal = view["account_type"].isin(["user", "admin"])
    hits = view[personal & (view["emp_id"] == "")]
    return _findings(
        hits,
        "Orphaned account",
        lambda r: f"{r.account} has no matching employee ID in HR",
    )


# --- Your turn --------------------------------------------------------------
# Remove the TODO body, write the rule, then un-skip its test.

def rule_contract_ended(view: pd.DataFrame, review_date: pd.Timestamp) -> list[Finding]:
    """A contractor whose end_date is before the review date.

    Hint: employment_type == "Contractor" and end_date < review_date.
    Category: "Contract ended"
    """
    hits = view[(view["employment_type"] == "Contractor") & (view["end_date"] < review_date)]
    return _findings(
        hits,
        "Contract ended",
        lambda r: f"{r.name}'s contract ended on {r.end_date:%d/%m/%Y} but {r.account} still has access",
    )


def rule_dormant_or_test(view: pd.DataFrame, review_date: pd.Timestamp) -> list[Finding]:
    """Test accounts, and enabled accounts with no sign-in for 90+ days.

    Hint: account_type == "test", OR (review_date - last_sign_in).days >= 90.
    Don't flag people on "Long-term leave", and skip break_glass accounts
    (they should never sign in). Watch out for empty last_sign_in (NaT).
    Category: "Dormant or test account"
    """
    days_since = (review_date - view["last_sign_in"]).dt.days
    dormant = (
        (days_since >= 90)
        & (view["enabled"] == "yes")
        & (view["status"] != "Long-term leave")
        & (view["account_type"] != "break_glass")
    )
    is_test = view["account_type"] == "test"
    hits = view[dormant | is_test]
    return _findings(
        hits,
        "Dormant or test account",
        lambda r: f"{r.account} ({r.account_type}) last signed in {r.last_sign_in:%d/%m/%Y}",
    )


def rule_service_account_risk(view: pd.DataFrame, review_date: pd.Timestamp) -> list[Finding]:
    """A service account with no named owner.

    Hint: account_type == "service" and owner == "".
    Category: "Service account risk"
    """
    hits = view[(view["account_type"] == "service") & (view["owner"] == "")]
    return _findings(
        hits,
        "Service account risk",
        lambda r: f"{r.account} is a service account with no named owner", 
    )


def rule_shared_account(view: pd.DataFrame, review_date: pd.Timestamp) -> list[Finding]:
    """Any grant held by a shared (generic) login.

    Hint: account_type == "shared".
    Category: "Shared account"
    """
    hits = view[view["account_type"] == "shared"]
    return _findings(
        hits,
        "Shared account",
        lambda r: f"{r.account} is shared login, so nobody is accountable for its use"
    )

SOD_PAIRS = [
    ("Supplier maintenance (create and amend suppliers)", "Approve payments"),
]


def rule_segregation_of_duties(view: pd.DataFrame, review_date: pd.Timestamp) -> list[Finding]:
    """One person holds both halves of a conflicting pair in SOD_PAIRS.

    Hint: group by emp_id (a person can have several accounts), and for each
    pair check whether the person's entitlements include both. Flag the
    grant for the FIRST entitlement in the pair (the one to remove).
    Category: "Segregation of duties"
    """
    return []  # TODO


def rule_excessive_privilege(view: pd.DataFrame, review_date: pd.Timestamp) -> list[Finding]:
    """Admin-tier access held on an everyday account.

    Hint: tier == "admin" and account_type in ("user", "guest").
    Admin roles belong on separate named admin accounts.
    Category: "Excessive privilege"
    """
    hits = view[(view["tier"] == "admin") & view["account_type"].isin(["user", "guest"])]
    return _findings(
        hits,
        "Excessive privilege",
        lambda r: f"{r.account} holds admin-tier '{r.entitlement}' on an everyday {r.account_type} account",
    )


def rule_standing_admin(view: pd.DataFrame, review_date: pd.Timestamp) -> list[Finding]:
    """A permanent Entra ID admin role on an admin account: make it just-in-time (PIM).

    Hint: system == "Entra ID", tier == "admin", assignment == "permanent",
    account_type == "admin". (Break-glass accounts are excluded by design.)
    Category: "Standing admin"
    """
    hits = view[
        (view["system"] == "Entra ID")
        & (view["tier"] == "admin")
        & (view["assignment"] == "permanent")
        & (view["account_type"] == "admin")
    ]
    return _findings(
        hits,
        "Standing admin",
        lambda r: f"{r.account} holds '{r.entitlement}' permanently: make it eligible through PIM",
    )


def rule_access_outside_department(view: pd.DataFrame, review_date: pd.Timestamp) -> list[Finding]:
    """Access meant for a different department than the person's current one.

    Hint: entitlement_department can hold several departments split by ";",
    or "All". Flag rows with an HR record where the person's department is
    not in that list. This is how movers' leftover access shows up.
    Category: "Role change (mover)"
    """
    return []  # TODO


ALL_RULES = [
    rule_leaver,
    rule_orphaned_account,
    rule_contract_ended,
    rule_dormant_or_test,
    rule_service_account_risk,
    rule_shared_account,
    rule_segregation_of_duties,
    rule_excessive_privilege,
    rule_standing_admin,
    rule_access_outside_department,
]
