#!/usr/bin/env python3
"""regenerate_office_hierarchy.py — regenerate office_hierarchy.json (the
all-office-types map Booking's views use) from the master roster file named
in pipeline_config.yaml (circle.master_roster_file).

Re-run this whenever the master roster changes (e.g. a regional
restructure). Division names are stored in short form; region is the
division's roster region (Roster.division_region), so every office of a
division sits in one region even if a stray source row says otherwise.
circle.division_merge is NOT applied here — short_div() applies it when
pipeline/sections/booking.py loads this file — so the file keeps each
office's real division.

Usage:
    python regenerate_office_hierarchy.py
"""
import json
import re
from pathlib import Path

import openpyxl

from pipeline.config import load_config
from pipeline.common import Roster, short_region

BASE = Path(__file__).parent
OUT = BASE / "office_hierarchy.json"


def _plain_div(s):
    return re.sub(r"\s+Divis(?:i)?on\s*$", "", str(s)).strip() if s else ""


def main():
    cfg = load_config()
    circle = cfg["circle"]
    roster = Roster.load(cfg)
    wb = openpyxl.load_workbook(BASE / circle["master_roster_file"], data_only=True, read_only=True)
    rows = wb[circle["master_roster_sheet"]].iter_rows(values_only=True)
    idx = {h: i for i, h in enumerate(next(rows))}
    out = {}
    for r in rows:
        if not r or r[idx["office_id"]] is None:
            continue
        oid = str(int(r[idx["office_id"]])) if isinstance(r[idx["office_id"]], float) else str(r[idx["office_id"]])
        div = _plain_div(r[idx["division_name"]])
        out[oid] = {
            "division": div,
            "region": roster.region_of(div, r[idx["region_name"]]) or short_region(r[idx["region_name"]]),
            "name": r[idx["office_name"]],
            "type": r[idx["office_type_code"]],
        }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"Wrote {OUT.name}: {len(out):,} offices")


if __name__ == "__main__":
    main()
