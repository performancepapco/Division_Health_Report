#!/usr/bin/env python3
"""
build_posb_june2026.py
───────────────────────
Reads the three standalone-month POSB reports (April, May, June 2026) and
builds a month-keyed POSB dataset:
  - POSB_BY_MONTH[month]["Anakapalle"] = {offices, opened, closed, net, region}
  - POSB_BY_MONTH[month]["__CIRCLE__"] / "__REG_<region>__" aggregates
  - office-level detail for Sub-Div Drilldown / BO Lookup (per month, to be summed)

Writes JSON files consumed by patch_june2026.py:
  _posb_by_month.json   (division/region/circle level, 3 months)
  _posb_offices.json     (office-level, 3 months, for subdiv/BO-lookup cumulative build)

Run:  python build_posb_june2026.py
"""
import json
from pathlib import Path
from collections import defaultdict
import openpyxl
import re

BASE = Path(__file__).parent
FILES = {
    "Apr-26": BASE / "uploads" / "june_2026" / "POSB" / "Merged_Product_Wise_AC_Report_April2026.xlsx",
    "May-26": BASE / "uploads" / "june_2026" / "POSB" / "Merged_Product_Wise_AC_Report_may2026.xlsx",
    "Jun-26": BASE / "uploads" / "june_2026" / "Merged_Product_Wise_AC_Report.xlsx",
}


def short_div(s):
    return re.sub(r"\s+Division\s*$", "", str(s)).strip() if s else ""


def short_region(s):
    return str(s).replace(" Region", "").strip() if s else ""


def read_month(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb["2. BO Totals"]

    offices = {}
    by_div = defaultdict(lambda: {"region": "", "offices": 0, "opened": 0, "closed": 0, "net": 0})
    by_reg = defaultdict(lambda: {"offices": 0, "opened": 0, "closed": 0, "net": 0})
    circle = {"offices": 0, "opened": 0, "closed": 0, "net": 0}

    for row in ws.iter_rows(min_row=2, values_only=True):
        oid = row[1]
        code_fallback = row[2]
        if not oid and not code_fallback:
            continue
        oid = str(oid) if oid else f"BOCODE_{code_fallback}"
        # Columns: Sl(0), Office ID(1), BO Code(2), Month(3), Name of the BO(4),
        # Name of the Sub Division(5), Name of the Division(6), Accounts Opened(7),
        # Accounts Closed(8), Net Addition(9), Region(10)
        code, name, sub_div, div, opened, closed, net, region = (
            row[2], row[4], row[5], row[6],
            row[7] or 0, row[8] or 0, row[9] or 0, row[10] or ""
        )
        div_s = short_div(div)
        reg_s = short_region(region)
        opened, closed, net = int(opened), int(closed), int(net)

        offices[oid] = {
            "code": code, "name": name, "type": "",
            "sub_division": sub_div or "(Unmapped)", "division": div_s, "region": reg_s,
            "opened": opened, "closed": closed, "net": net,
        }

        d = by_div[div_s]
        d["region"] = reg_s
        d["offices"] += 1
        d["opened"] += opened
        d["closed"] += closed
        d["net"] += net

        r = by_reg[reg_s]
        r["offices"] += 1
        r["opened"] += opened
        r["closed"] += closed
        r["net"] += net

        circle["offices"] += 1
        circle["opened"] += opened
        circle["closed"] += closed
        circle["net"] += net

    return offices, dict(by_div), dict(by_reg), circle


def main():
    posb_by_month = {}
    offices_by_month = {}

    for month, path in FILES.items():
        print(f"Reading {path.name} ({month})...")
        offices, by_div, by_reg, circle = read_month(path)
        print(f"  {len(offices)} offices, {len(by_div)} divisions, circle net={circle['net']:+,}")

        month_data = {}
        for div, d in by_div.items():
            month_data[div] = {
                "offices": d["offices"], "opened": d["opened"],
                "closed": d["closed"], "net": d["net"], "region": d["region"],
            }
        for reg, r in by_reg.items():
            month_data[f"__REG_{reg}__"] = {
                "offices": r["offices"], "opened": r["opened"],
                "closed": r["closed"], "net": r["net"],
            }
        month_data["__CIRCLE__"] = circle

        posb_by_month[month] = month_data
        offices_by_month[month] = offices

    out_dir = BASE
    (out_dir / "_posb_by_month.json").write_text(
        json.dumps(posb_by_month, ensure_ascii=False), encoding="utf-8")
    (out_dir / "_posb_offices.json").write_text(
        json.dumps(offices_by_month, ensure_ascii=False), encoding="utf-8")
    print("\nWrote _posb_by_month.json and _posb_offices.json")

    # Sanity: Apr + May + June circle totals
    tot_net = sum(posb_by_month[m]["__CIRCLE__"]["net"] for m in FILES)
    tot_opened = sum(posb_by_month[m]["__CIRCLE__"]["opened"] for m in FILES)
    tot_closed = sum(posb_by_month[m]["__CIRCLE__"]["closed"] for m in FILES)
    print(f"\nApr+May+Jun circle totals -> opened={tot_opened:,} closed={tot_closed:,} net={tot_net:+,}")


if __name__ == "__main__":
    main()
