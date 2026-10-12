"""Run every rule, write findings and a report, and score against the answer key.

Usage:  python -m access_review.run
"""
from collections import defaultdict
from pathlib import Path

import pandas as pd

from access_review.loader import load_answer_key, load_view
from access_review.rules import ALL_RULES

REVIEW_DATE = pd.Timestamp("2026-10-12")
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def run_rules(view: pd.DataFrame) -> list:
    findings = []
    for rule in ALL_RULES:
        findings.extend(rule(view, REVIEW_DATE))
    return findings


def score(findings, key: pd.DataFrame) -> dict:
    flagged = defaultdict(set)
    for f in findings:
        flagged[f.grant_id].add(f.category)
    issues = key[key["expected_decision"] != "keep"]
    keeps = set(key.loc[key["expected_decision"] == "keep", "grant_id"])
    found = [g for g in issues["grant_id"] if g in flagged]
    right_cat = [
        r.grant_id for r in issues.itertuples() if r.expected_category in flagged.get(r.grant_id, set())
    ]
    return {
        "issues": len(issues),
        "found": found,
        "missed": [g for g in issues["grant_id"] if g not in flagged],
        "right_category": right_cat,
        "false_positives": sorted(g for g in flagged if g in keeps),
    }


def write_report(findings, result, view) -> str:
    by_cat = defaultdict(list)
    for f in findings:
        by_cat[f.category].append(f)
    lines = [
        "# Access review findings",
        "",
        f"Review date: {REVIEW_DATE:%d/%m/%Y}  ",
        f"Grants reviewed: {len(view)}  ",
        f"Findings: {len(findings)} across {len({f.grant_id for f in findings})} grants",
        "",
    ]
    for cat in sorted(by_cat):
        lines.append(f"## {cat} ({len(by_cat[cat])})")
        lines.append("")
        for f in sorted(by_cat[cat], key=lambda x: x.grant_id):
            lines.append(f"- **{f.grant_id}** `{f.account}`: {f.detail}")
        lines.append("")
    lines += [
        "## Score against the answer key",
        "",
        f"- Issues found: {len(result['found'])}/{result['issues']}",
        f"- Right category: {len(result['right_category'])}/{result['issues']}",
        f"- False positives: {len(result['false_positives'])} {result['false_positives'] or ''}",
        f"- Missed: {', '.join(result['missed']) or 'none'}",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    view = load_view()
    findings = run_rules(view)
    result = score(findings, load_answer_key())

    OUTPUT_DIR.mkdir(exist_ok=True)
    pd.DataFrame([f.__dict__ for f in findings]).to_csv(OUTPUT_DIR / "findings.csv", index=False)
    (OUTPUT_DIR / "report.md").write_text(write_report(findings, result, view), encoding="utf-8")

    print(f"Findings: {len(findings)}")
    for f in findings:
        print(f"  {f.grant_id:4} {f.category:24} {f.detail}")
    print()
    print(f"Issues found:      {len(result['found'])}/{result['issues']}")
    print(f"Right category:    {len(result['right_category'])}/{result['issues']}")
    print(f"False positives:   {len(result['false_positives'])} {result['false_positives'] or ''}")
    print(f"Still to catch:    {', '.join(result['missed']) or 'none - well done'}")
    print(f"\nWrote {OUTPUT_DIR / 'findings.csv'} and {OUTPUT_DIR / 'report.md'}")


if __name__ == "__main__":
    main()
