"""Load the three exports and join them into one review view."""
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_view(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """Return one row per grant, with the account and HR record joined on.

    grants --(account)--> accounts --(emp_id)--> hr

    Grants whose account has no HR match keep empty HR columns: those are
    the orphaned accounts.
    """
    hr = pd.read_csv(data_dir / "hr.csv", dtype=str).fillna("")
    accounts = pd.read_csv(data_dir / "accounts.csv", dtype=str).fillna("")
    grants = pd.read_csv(data_dir / "grants.csv", dtype=str).fillna("")

    view = grants.merge(accounts, on="account", how="left", validate="many_to_one")
    view = view.merge(hr, on="emp_id", how="left", validate="many_to_one").fillna("")

    for col in ("last_sign_in", "end_date", "move_date"):
        view[col] = pd.to_datetime(view[col], errors="coerce")
    return view


def load_answer_key(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    return pd.read_csv(data_dir / "answer_key.csv", dtype=str).fillna("")
