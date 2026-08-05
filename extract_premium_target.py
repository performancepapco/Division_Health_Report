#!/usr/bin/env python3
"""extract_premium_target.py — extracts PLI/RPLI Premium Target & Achievement
(division-wise) from a manually-uploaded workbook with four sheets:
  "PLI NBP", "PLI TBP", "RPLI NBP", "RPLI TBP"
(New Business Premium / Total Business Premium, one sheet per product).

This is NOT part of the Form-driven monthly pipeline yet (no upload slot
exists for it) — matching how BO Lookup Silent Accounts' first month was
handled before its own Form section existed. Re-run this by hand each month
against that month's workbook (see --file/--month/--label below); there is
still no automated upload path for it.

NBP and TB are genuinely different figures (Total Business = new + renewal
premium; New Business = only fresh policies), so both are kept, not merged
— the front end toggles between them.

Column layout is detected by locating the "S.No" header cell and reading
every other column at a fixed *offset* from it, rather than a hardcoded
absolute index — the June-2026 workbooks had a leading blank column A that
the July-2026 workbook doesn't, and this keeps the script working across
that kind of drift without needing a rewrite each time.

Output: data/premium_target.json, division-keyed with the same slug()
convention as pipeline/derive/trends.py (lowercase, space->hyphen) so the
front end can join it against trends.json's division keys directly.

Usage:
    python extract_premium_target.py \\
        --file "uploads/July_2026/PLI_RPLI_NBP_TBP_Target_vs_Achievement_July_2026.xlsx" \\
        --month 2026-07 --label "July-2026"
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import openpyxl

BASE = Path(__file__).parent
DATA_DIR = BASE / "data"

PRODUCTS = ["PLI", "RPLI"]
BASES = {"nbp": "NBP", "tb": "TBP"}

# Column offsets relative to the "S.No" header cell, shared by every sheet.
OFF_REGION, OFF_DIV = 1, 2
OFF_TARGET, OFF_PRORATA, OFF_ACH = 4, 5, 6
OFF_PCT_PRORATA, OFF_PCT_ACTUAL = 7, 8
OFF_PREV_YEAR, OFF_YOY = 9, 10


def _slug(name: str) -> str:
    return "-".join(name.lower().split())


def _find_header(rows: list[tuple]) -> tuple[int, int]:
    """Locate the (row, col) of the "S.No" header cell."""
    for i, r in enumerate(rows):
        for j, cell in enumerate(r):
            if cell == "S.No":
                return i, j
    raise ValueError('no "S.No" header cell found')


def _read_sheet(path: Path, sheet: str) -> tuple[dict, dict]:
    """Returns (divisions, circle) for one product+basis sheet. divisions is
    slug -> {name, region, target, prorata_target, achievement,
    pct_prorata, pct_actual, prev_year_achievement, yoy_growth_pct}."""
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb[sheet]
    rows = list(ws.iter_rows(values_only=True))
    hdr_row, c = _find_header(rows)

    def cell(r, off):
        idx = c + off
        return r[idx] if idx < len(r) else None

    divisions = {}
    circle = None
    for r in rows[hdr_row + 1:]:
        sno = cell(r, 0)
        if sno is None:
            continue
        if str(sno).strip() == "Grand total":
            circle = {
                "target": round(cell(r, OFF_TARGET) or 0, 4),
                "prorata_target": round(cell(r, OFF_PRORATA) or 0, 4),
                "achievement": round(cell(r, OFF_ACH) or 0, 4),
                "pct_prorata": round(cell(r, OFF_PCT_PRORATA) or 0, 4),
                "pct_actual": round(cell(r, OFF_PCT_ACTUAL) or 0, 4),
            }
            continue
        if circle is not None:
            continue  # past the division block (region summary rows follow)
        div_name = str(cell(r, OFF_DIV)).strip()
        region = str(cell(r, OFF_REGION)).strip().lower()
        yoy = cell(r, OFF_YOY)
        divisions[_slug(div_name)] = {
            "name": div_name, "region": region,
            "target": round(cell(r, OFF_TARGET) or 0, 4),
            "prorata_target": round(cell(r, OFF_PRORATA) or 0, 4),
            "achievement": round(cell(r, OFF_ACH) or 0, 4),
            "pct_prorata": round(cell(r, OFF_PCT_PRORATA) or 0, 4),
            "pct_actual": round(cell(r, OFF_PCT_ACTUAL) or 0, 4),
            "prev_year_achievement": round(cell(r, OFF_PREV_YEAR) or 0, 4),
            "yoy_growth_pct": round(yoy, 4) if yoy is not None else None,
        }
    if circle is None:
        sys.exit(f"ERROR: no 'Grand total' row found in {path.name}::{sheet}")
    return divisions, circle


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, type=Path,
                     help="Path to the PLI/RPLI NBP+TBP Target vs Achievement workbook.")
    ap.add_argument("--month", required=True, help="Reporting month, YYYY-MM (e.g. 2026-07).")
    ap.add_argument("--label", required=True, help='Display label for the source note (e.g. "July-2026").')
    args = ap.parse_args()

    if not args.file.exists():
        sys.exit(f"ERROR: expected file not found: {args.file}")

    out_divisions = {}
    out_circle = {}
    for product in PRODUCTS:
        for basis, sheet_suffix in BASES.items():
            sheet = f"{product} {sheet_suffix}"
            divisions, circle = _read_sheet(args.file, sheet)
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
            "data_as_on": args.month,
            "source": f"PLI RPLI NBP/TBP Target vs Achievement - Upto {args.label} (manual upload, {args.file.as_posix()})",
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
