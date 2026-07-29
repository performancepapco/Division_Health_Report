"""TRENDS — FY-target attainment series for data/trends.json.

Ports the pro-ration/attainment formulas that today only exist client-side
in index.html:
  - PRORATION_CONFIG.compute (index.html:3790-3792): pro_rata_target =
    fy_target * months_elapsed / 12
  - recalcDerived (index.html:3911-3923): pct_prorata =
    achievement / pro_rata_target * 100 (0 if pro_rata_target <= 0)

FY targets have NO Python-readable source today — index.html's hand-
authored DATA_BY_MONTH['Apr-26'].targets is the only copy anywhere. This
module reads data/targets.json instead, a static one-time snapshot
produced by migrate_ecr_targets.py. There is no monthly upload path for
targets; if FY targets are ever revised mid-year, or a new division is
added to known_divisions, data/targets.json must be hand-edited — known
gap, not something this module can detect.

Known scope limit: PLI and RPLI share one combined "PLI/RPLI" FY target/
actual (no separate target exists for the split), so pli_rpli is reported
as a single combined vertical only.
"""
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).parent.parent.parent
DATA_DIR = BASE / "data"

# Existing display-string keys -> clean lowercase keys for this new
# contract only. Do NOT rename anything in the existing codebase.
VERTICAL_KEYS = {
    "Parcel": "parcel",
    "Mail Operations": "mail_ops",
    "IR & GB": "irgb",
    "CCS": "ccs",
    "POSB": "posb",
    "PLI/RPLI": "pli_rpli",
}

REGION_ABBR = {"Vijayawada": "vja", "Visakhapatnam": "vsp", "Kurnool": "knl"}
SOURCE_LABEL = "CEPT MIS / PFMS"


def _slug(name: str) -> str:
    return "-".join(name.lower().split())


def _fy_and_months_elapsed(month_iso: str) -> tuple[str, int]:
    """FY is Apr-Mar. '2026-06' -> ('2026-27', 3)."""
    y, m = (int(x) for x in month_iso.split("-"))
    fy_start = y if m >= 4 else y - 1
    fy_label = f"{fy_start}-{str(fy_start + 1)[2:]}"
    months_elapsed = ((m - 4) % 12) + 1
    return fy_label, months_elapsed


def _load_ecr_divisions(month_iso: str) -> dict:
    p = DATA_DIR / f"dataset_{month_iso}.json"
    if not p.exists():
        return {}
    dataset = json.loads(p.read_text(encoding="utf-8"))
    section = dataset["sections"].get("ecr")
    return section["standalone"].get("divisions", {}) if section else {}


def _has_ecr(month_iso: str) -> bool:
    p = DATA_DIR / f"dataset_{month_iso}.json"
    if not p.exists():
        return False
    dataset = json.loads(p.read_text(encoding="utf-8"))
    return "ecr" in dataset.get("sections", {})


def _load_targets() -> dict:
    p = DATA_DIR / "targets.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def build(cfg: dict, months: list[str]) -> dict:
    # Every vertical here (including "posb"/"pli_rpli") is sourced from the
    # ecr dataset section's own "actuals" breakdown, not from the separate
    # booking/posb sections — so a month whose ecr file hasn't been
    # uploaded yet has to be dropped here, not just zero-filled. Left in,
    # it would still be treated as "the latest month" (assemble.py's
    # months list is any month with *a* dataset file, and booking/posb are
    # now uploaded daily ahead of ecr) and would silently zero out every
    # division's pct_prorata for that month — flags.py then finds no one
    # below a circle average of 0 and the whole below-average watchlist
    # goes empty, which reads as "nothing's underperforming" rather than
    # the true "ecr isn't uploaded for this month yet."
    months = [m for m in months if _has_ecr(m)]

    known_divisions = cfg["sections"]["ecr"]["known_divisions"]
    targets = _load_targets()
    ecr_by_month = {m: _load_ecr_divisions(m) for m in months}

    circle_fy_target = defaultdict(float)
    circle_monthly_sums = {vkey: {m: {"ach": 0.0, "pr": 0.0} for m in months}
                            for vkey in VERTICAL_KEYS.values()}
    divisions_out = {}

    for div_name in known_divisions:
        tgt_rec = targets.get(div_name)
        if not tgt_rec:
            print(f"  WARNING: {div_name} missing from data/targets.json — skipped in trends.json")
            continue
        region_full = tgt_rec.get("region", "")
        region_abbr = REGION_ABBR.get(region_full, region_full.lower())
        div_targets = tgt_rec.get("targets", {})

        verticals_out = {}
        for disp_key, vkey in VERTICAL_KEYS.items():
            fy_target = div_targets.get(disp_key, 0) or 0
            circle_fy_target[vkey] += fy_target
            monthly = []
            for month in months:
                _, months_elapsed = _fy_and_months_elapsed(month)
                pro_rata_target = fy_target * months_elapsed / 12
                achievement = (ecr_by_month[month].get(div_name, {})
                               .get("actuals", {}).get(disp_key, 0)) or 0
                pct_prorata = (achievement / pro_rata_target * 100) if pro_rata_target > 0 else 0
                monthly.append({
                    "month": month,
                    "prorata_target": round(pro_rata_target, 4),
                    "achievement": round(achievement, 4),
                    "pct_prorata": round(pct_prorata, 4),
                })
                circle_monthly_sums[vkey][month]["ach"] += achievement
                circle_monthly_sums[vkey][month]["pr"] += pro_rata_target
            verticals_out[vkey] = {"fy_target": round(fy_target, 4), "monthly": monthly}

        divisions_out[_slug(div_name)] = {
            "name": div_name, "region": region_abbr, "verticals": verticals_out,
        }

    circle_out = {}
    for vkey, per_month in circle_monthly_sums.items():
        monthly = []
        for month in months:
            s = per_month[month]
            pct = (s["ach"] / s["pr"] * 100) if s["pr"] > 0 else 0
            monthly.append({
                "month": month, "prorata_target": round(s["pr"], 4),
                "achievement": round(s["ach"], 4), "pct_prorata": round(pct, 4),
            })
        circle_out[vkey] = {"fy_target": round(circle_fy_target[vkey], 4), "monthly": monthly}

    fy_label = _fy_and_months_elapsed(months[-1])[0] if months else None
    return {
        "meta": {
            "generated_on": datetime.now(timezone.utc).isoformat(),
            "data_as_on": months[-1] if months else None,
            "source": SOURCE_LABEL,
            "fy": fy_label,
            "months": months,
        },
        "circle": {"verticals": circle_out},
        "divisions": divisions_out,
    }
