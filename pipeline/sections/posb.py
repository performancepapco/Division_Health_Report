"""POSB — Accounts Opened/Closed.

Standalone-month activity sheet: offices with zero activity are simply
absent from it, which understates "offices" per division. The true office
universe comes from the master roster (see pipeline.common.Roster), unioned
with this month's activity IDs (an office with real activity but missing
from the roster — "hierarchy drift" — is still a real office; folded in
rather than dropped).

Note: unlike the legacy build_posb_june2026.py (which pooled activity IDs
across all 3 hardcoded months before computing office universes), this
computes the union per-month since each run only sees one month's file.
A division's "offices" figure may shift very slightly run-to-run if a
drifted office's first appearance moves between months — it converges once
the roster is updated, and does not affect opened/closed/net (a NIL office
contributes 0 to those regardless).

No cross-month merge happens here (cumulative_mode: none) — the dashboard
sums opened/closed/net across the selected month range client-side
(getPOSBData in index.html); see Phase 2 notes.
"""
import re
from collections import defaultdict
import openpyxl

from pipeline.validate import validate_xlsx_sheet, ValidationError
from pipeline.common import short_div, short_region, Roster, iso_to_label
from pipeline.config import load_config

SHEET = "2. BO Totals"
SCHEME_SHEET = "1. Scheme-wise Detail"
POSB_SCHEMES = ["MIS", "PPFGP", "SSA", "RD", "SBBAS", "SBSGP", "SCSS", "TD",
                "PRFTS", "KVN", "NSC8", "MSSC"]


def validate(section_cfg: dict, path, month_iso: str) -> list[ValidationError]:
    sheet_cfg = section_cfg["sheets"][SHEET]
    errors = validate_xlsx_sheet("posb", "POSB file", path, SHEET, sheet_cfg)
    if errors:
        return errors

    # Month-in-file check: the "Month" column holds a date range like
    # "01-06-2026 - 30-06-2026" (DD-MM-YYYY). Compare its month/year against
    # the declared month for the first data row (all rows share one range).
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    ws = wb[SHEET]
    rows = ws.iter_rows(min_row=2, values_only=True)
    first = next(rows, None)
    if first is None:
        return [ValidationError("posb", "POSB file: no data rows found below the header.")]
    month_col = first[3]
    m = re.search(r"-(\d{2})-(\d{4})", str(month_col) or "")
    if m:
        file_month, file_year = m.group(1), m.group(2)
        declared_month = month_iso[5:7]
        declared_year = month_iso[:4]
        if file_month != declared_month or file_year != declared_year:
            return [ValidationError("posb",
                f"POSB file: 'Month' column says {month_col!r} but you declared "
                f"{iso_to_label(month_iso)} in the Form — please upload the POSB "
                f"file for the month you selected.")]
    return []


def _read_schemes(wb) -> dict:
    """'1. Scheme-wise Detail' — per-office scheme breakdown, consumed only
    by the derived BO_LOOKUP view (pipeline/derive/subdiv_bolookup.py), not
    by anything in this section's own by_div/by_reg/circle rollups. Kept
    positional (base = 7 + i*3 per scheme), matching the source report's
    lack of stable per-scheme headers — same approach the legacy
    build_subdiv_bolookup_june2026.py used."""
    if SCHEME_SHEET not in wb.sheetnames:
        return {}
    ws = wb[SCHEME_SHEET]
    schemes = defaultdict(dict)
    for row in ws.iter_rows(min_row=2, values_only=True):
        oid, code = row[1], row[2]
        if not oid and not code:
            continue
        oid = str(oid) if oid else f"BOCODE_{code}"
        sch = {}
        for i, name in enumerate(POSB_SCHEMES):
            base = 7 + i * 3
            o, c, n = int(row[base] or 0), int(row[base + 1] or 0), int(row[base + 2] or 0)
            if o == 0 and c == 0 and n == 0:
                continue
            sch[name] = {"o": o, "c": c, "n": n}
        if sch:
            schemes[oid] = sch
    return dict(schemes)


def extract(section_cfg: dict, path, month_iso: str) -> dict:
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb[SHEET]

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

    roster = Roster.load(load_config())
    activity_ids_by_div = defaultdict(set)
    activity_ids_by_reg = defaultdict(set)
    for oid, rec in offices.items():
        activity_ids_by_div[rec["division"]].add(oid)
        activity_ids_by_reg[rec["region"]].add(oid)

    real_divisions = set(by_div.keys())
    final_ids_by_div = {
        div: roster.ids_by_div.get(div, set()) | activity_ids_by_div.get(div, set())
        for div in real_divisions
    }
    final_ids_by_reg = {
        reg: roster.ids_by_reg.get(reg, set()) | activity_ids_by_reg.get(reg, set())
        for reg in set(roster.ids_by_reg) | set(activity_ids_by_reg)
    }
    master_div_counts = {div: len(ids) for div, ids in final_ids_by_div.items()}
    master_reg_counts = {reg: len(ids) for reg, ids in final_ids_by_reg.items()}
    master_circle_count = len(set().union(*final_ids_by_div.values())) if final_ids_by_div else 0

    month_data = {}
    for div, d in by_div.items():
        month_data[div] = {
            "offices": master_div_counts.get(div, d["offices"]), "opened": d["opened"],
            "closed": d["closed"], "net": d["net"], "region": d["region"],
        }
    for reg, r in by_reg.items():
        month_data[f"__REG_{reg}__"] = {
            "offices": master_reg_counts.get(reg, r["offices"]), "opened": r["opened"],
            "closed": r["closed"], "net": r["net"],
        }
    month_data["__CIRCLE__"] = dict(circle, offices=master_circle_count)

    schemes = _read_schemes(wb)

    return {"divisions": month_data, "offices": offices, "schemes": schemes}


def merge_cumulative(new_slice: dict, previous_cumulative: dict | None) -> dict:
    # cumulative_mode: none — the dashboard sums opened/closed/net across the
    # selected month range client-side; nothing to merge server-side.
    return new_slice


def row_count(data: dict) -> int:
    return len(data.get("offices", {})) if data else 0
