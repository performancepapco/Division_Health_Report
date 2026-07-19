#!/usr/bin/env python3
"""extract_premium_target.py — extracts PLI/RPLI Premium Target & Achievement
(division-wise) from the two manually-uploaded workbooks under
uploads/june_2026/Insurance/:
  - "PLI RPLI NBP- Upto June-26.xlsx"  (New Business Premium)
  - "PLI RPLI TB- Upto June-26.xlsx"   (Total Business Premium)

These are NOT part of the Form-driven monthly pipeline yet (no upload slot
exists for them) — this is a one-off extraction for the June-2026 data,
matching how BO Lookup Silent Accounts' first month was handled before its
own Form section existed. A recurring monthly upload path is a follow-up,
not done here.

NBP and TB are genuinely different figures (Total Business = new + renewal
premium; New Business = only fresh policies — confirmed against the
workbooks: PLI's circle-wide TB target is Rs.1,360 Cr vs NBP's Rs.340 Cr),
so both are kept, not merged — the front end toggles between them.

Output: data/premium_target.json, division-keyed with the same slug()
convention as pipeline/derive/trends.py (lowercase, space->hyphen) so the
front end can join it against trends.json's division keys directly.
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import openpyxl

BASE = Path(__file__).parent
INSURANCE_DIR = BASE / "uploads" / "june_2026" / "Insurance"
DATA_DIR = BASE / "data"

FILES = {
    "nbp": INSURANCE_DIR / "PLI RPLI NBP- Upto June-26.xlsx",
    "tb":  INSURANCE_DIR / "PLI RPLI TB- Upto June-26.xlsx",
}
PRODUCTS = ["PLI", "RPLI"]
DATA_AS_ON = "2026-06"


def _slug(name: str) -> str:
    return "-".join(name.lower().split())


def _read_sheet(path: Path, sheet: str) -> tuple[dict, dict]:
    """Returns (divisions, circle) for one product-sheet. divisions is
    slug -> {name, region, target, prorata_target, achievement,
    pct_prorata, pct_actual, prev_year_achievement, yoy_growth_pct}."""
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb[sheet]
    rows = list(ws.iter_rows(values_only=True))
    hdr_idx = next(i for i, r in enumerate(rows) if r[1] == "S.No")
    divisions = {}
    circle = None
    for r in rows[hdr_idx + 1:]:
        if r[1] is None:
            continue
        if r[1] == "Grand total":
            circle = {
                "target": round(r[5] or 0, 4), "prorata_target": round(r[6] or 0, 4),
                "achievement": round(r[7] or 0, 4), "pct_prorata": round(r[8] or 0, 4),
                "pct_actual": round(r[9] or 0, 4),
            }
            continue
        if circle is not None:
            continue  # past the division block (region summary rows follow)
        div_name = str(r[3]).strip()
        region = str(r[2]).strip().lower()
        divisions[_slug(div_name)] = {
            "name": div_name, "region": region,
            "target": round(r[5] or 0, 4), "prorata_target": round(r[6] or 0, 4),
            "achievement": round(r[7] or 0, 4), "pct_prorata": round(r[8] or 0, 4),
            "pct_actual": round(r[9] or 0, 4),
            "prev_year_achievement": round(r[10] or 0, 4),
            "yoy_growth_pct": round(r[11] or 0, 4) if r[11] is not None else None,
        }
    if circle is None:
        sys.exit(f"ERROR: no 'Grand total' row found in {path.name}::{sheet}")
    return divisions, circle


def main():
    for basis, path in FILES.items():
        if not path.exists():
            sys.exit(f"ERROR: expected file not found: {path}")

    out_divisions = {}
    out_circle = {}
    for basis, path in FILES.items():
        for product in PRODUCTS:
            divisions, circle = _read_sheet(path, product)
            pkey = product.lower()
            out_circle.setdefault(pkey, {})[basis] = circle
            for slug, rec in divisions.items():
                out_divisions.setdefault(slug, {"name": rec["name"], "region": rec["region"], "products": {}})
                out_divisions[slug]["products"].setdefault(pkey, {})[basis] = {
                    k: v for k, v in rec.items() if k not in ("name", "region")
                }

    out = {
        "meta": {
            "generated_on": datetime.now(timezone.utc).isoformat(),
            "data_as_on": DATA_AS_ON,
            "source": "PLI RPLI NBP/TB — Upto June-26 (manual upload, uploads/june_2026/Insurance/)",
        },
        "circle": out_circle,
        "divisions": out_divisions,
    }
    out_path = DATA_DIR / "premium_target.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Wrote {out_path} ({len(out_divisions)} divisions)")
    sample = next(iter(out_divisions.values()))
    print("Sample:", json.dumps(sample, indent=2)[:600])


if __name__ == "__main__":
    main()
