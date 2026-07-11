"""PLI/RPLI __CUM__ — the one field (offices_procured) that can't be summed
across months client-side the way policies/premium already are (a distinct-
office count, not additive — an office procuring in both April and May must
count once over the range, not twice). The legacy pipeline got this from a
separately-uploaded "Apr-to-<month> cumulative distribution" file; per the
already-confirmed Form section list (no such upload exists), this derives
it instead from the office-level Detail records this pipeline already
extracts each month — the union of office codes with policies > 0 across
all months on record.

Office 'code' (not office name) is the join key here — it's PLI/RPLI's own
internal numbering, stable month to month within that report (unlike POSB's
ID scheme, no roster join is needed for this specific calculation).
"""
import json
from pathlib import Path
from collections import defaultdict

BASE = Path(__file__).parent.parent.parent
DATA_DIR = BASE / "data"


def _load_offices(month_iso: str, segment: str) -> list:
    p = DATA_DIR / f"dataset_{month_iso}.json"
    if not p.exists():
        return []
    dataset = json.loads(p.read_text(encoding="utf-8"))
    section = dataset["sections"].get(segment)
    return section["standalone"].get("offices", []) if section else []


def _load_divisions(month_iso: str, segment: str) -> dict:
    p = DATA_DIR / f"dataset_{month_iso}.json"
    if not p.exists():
        return {}
    dataset = json.loads(p.read_text(encoding="utf-8"))
    section = dataset["sections"].get(segment)
    return section["standalone"].get("divisions", {}) if section else {}


def build_cum(months: list[str], segment: str) -> dict:
    procured_codes = defaultdict(set)   # division -> set(code)
    policies = defaultdict(int)
    premium = defaultdict(float)
    total_offices = {}                  # division -> latest known total_offices

    for month in months:
        for rec in _load_offices(month, segment):
            div = rec["division"]
            if rec["policies"] > 0:
                procured_codes[div].add(rec["code"])
            policies[div] += rec["policies"]
            premium[div] += rec["premium"]
        for div, d in _load_divisions(month, segment).items():
            if div == "__CIRCLE__":
                continue
            total_offices[div] = d["total_offices"]

    out = {}
    all_divs = set(procured_codes) | set(policies) | set(total_offices)
    circle_offices_procured = 0
    circle_policies = 0
    circle_premium = 0.0
    circle_total_offices = 0
    for div in all_divs:
        offices_procured = len(procured_codes.get(div, set()))
        out[div] = {
            "total_offices": total_offices.get(div, 0),
            "offices_procured": offices_procured,
            "policies": policies.get(div, 0),
            "premium": round(premium.get(div, 0.0), 2),
        }
        circle_offices_procured += offices_procured
        circle_policies += policies.get(div, 0)
        circle_premium += premium.get(div, 0.0)
        circle_total_offices += total_offices.get(div, 0)

    out["__CIRCLE__"] = {
        "total_offices": circle_total_offices,
        "offices_procured": circle_offices_procured,
        "policies": circle_policies,
        "premium": round(circle_premium, 2),
    }
    return out
