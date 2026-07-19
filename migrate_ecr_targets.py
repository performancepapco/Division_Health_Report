#!/usr/bin/env python3
"""migrate_ecr_targets.py — ONE-TIME migration, run exactly once and its
output committed. Do not re-run against a changed index.html without
re-reading this docstring; it aborts loudly if data/dataset_2026-04.json
already has an "ecr" section (idempotency guard) or if the expected
DATA_BY_MONTH/OFFICE_ENTRIES shapes have moved.

Extracts two things baked into index.html (never written by the Python
pipeline until now):
  1. FY targets + region per division -> data/targets.json (33 known
     divisions only; the 6 circle_full_extra_rows have all-zero targets
     and are intentionally excluded).
  2. April 2026's ECR actuals/expenditure/swap -> retrofitted into
     data/dataset_2026-04.json as a real "ecr" section, in the same
     shape pipeline/sections/ecr.py's extract() normally produces, so
     assemble.py and pipeline/derive/trends.py can treat April exactly
     like May/June with no special-casing.

index.html itself is NOT modified by this script.
"""
import json
import re
import sys
from pathlib import Path

from pipeline.config import load_config, get_section

BASE = Path(__file__).parent
DATA_DIR = BASE / "data"
CR_ACTUAL_KEYS = ["Parcel", "Mail Operations", "IR & GB", "CCS", "POSB", "PLI/RPLI", "Total"]
SWAP_KEYS = ["Salaries", "Wages", "Pension", "Allowances", "Plan", "Other"]


def extract_data_by_month(html: str) -> dict:
    """Isolates DATA_BY_MONTH's value with a JSON decoder (raw_decode),
    NOT a naive rstrip(';') slice — robust to whatever trails the value."""
    m = re.search(r"\bconst\s+DATA_BY_MONTH\s*=\s*", html)
    if not m:
        sys.exit("ERROR: 'const DATA_BY_MONTH' not found — already migrated, or file changed?")
    obj, _ = json.JSONDecoder().raw_decode(html, m.end())
    if list(obj.keys()) != ["Apr-26"]:
        sys.exit(f"ERROR: expected DATA_BY_MONTH to have exactly one key 'Apr-26', got {list(obj.keys())}")
    return obj["Apr-26"]


def extract_office_entries(html: str) -> dict:
    """OFFICE_ENTRIES is a hand-authored JS object literal (unquoted keys,
    trailing comma) — not valid JSON. Finds the declaration boundary, then
    a bounded per-row/per-field regex (safe here: 6 rows, fixed shape)."""
    m = re.search(r"const\s+OFFICE_ENTRIES\s*=\s*\{", html)
    if not m:
        sys.exit("ERROR: 'const OFFICE_ENTRIES' not found — already migrated, or file changed?")
    start = m.end() - 1
    end = html.find("};", start)
    if end < 0:
        sys.exit("ERROR: no closing '};' found for OFFICE_ENTRIES")
    body = html[start:end + 1]
    entries = {}
    for row_m in re.finditer(r'"([^"]+)":\s*\{([^}]*)\}', body):
        name, raw_fields = row_m.groups()
        fields = {}
        for fm in re.finditer(r'(\w+):\s*("(?:[^"\\]|\\.)*"|-?[\d.]+)', raw_fields):
            key, val = fm.groups()
            fields[key] = val.strip('"') if val.startswith('"') else float(val)
        entries[name] = fields
    return entries


def build_targets_json(apr_data: dict, known_divisions: list[str]) -> dict:
    out = {}
    missing = []
    for name in known_divisions:
        rec = apr_data.get(name)
        if not rec or "targets" not in rec:
            missing.append(name)
            continue
        out[name] = {"region": rec["region"], "targets": rec["targets"]}
    if missing:
        sys.exit(f"ERROR: known_divisions missing from DATA_BY_MONTH['Apr-26']: {missing}")
    return out


def build_extra_row_division(fields: dict) -> dict:
    """Mirrors OFFICE_ENTRIES' own front-end reconstruction exactly
    (index.html:3714-3737) — Parcel/IRGB/POSB default to 0 (never present
    in OFFICE_ENTRIES), swap only carries Pension (no further breakdown
    exists anywhere for these admin rows — a pre-existing limitation of
    the hand-authored data, not something this migration loses)."""
    parcel = fields.get("Parcel", 0.0)
    mo = fields.get("MO", 0.0)
    irgb = fields.get("IRGB", 0.0)
    ccs = fields.get("CCS", 0.0)
    posb = fields.get("POSB", 0.0)
    pli_rpli = fields.get("PLIRPLI", 0.0)
    total_exp = fields.get("total_exp", 0.0)
    pension = fields.get("pension", 0.0)
    actuals = {
        "Parcel": round(parcel, 7), "Mail Operations": round(mo, 7),
        "IR & GB": round(irgb, 7), "CCS": round(ccs, 7),
        "POSB": round(posb, 7), "PLI/RPLI": round(pli_rpli, 7),
        "Total": round(parcel + mo + irgb + ccs + posb + pli_rpli, 7),
    }
    swap = {"Salaries": 0.0, "Wages": 0.0, "Pension": round(pension, 7),
            "Allowances": 0.0, "Plan": 0.0, "Other": 0.0, "Total": round(total_exp, 7)}
    return {"actuals": actuals, "total_exp": round(total_exp, 7), "swap": swap}


def build_circle_full(divisions: dict, all_row_names: set) -> dict:
    """Replicates pipeline/sections/ecr.py's _extract_circle_full formula
    exactly (same round(v, 4) convention)."""
    actuals = {k: 0.0 for k in CR_ACTUAL_KEYS}
    total_exp = 0.0
    swap = {k: 0.0 for k in SWAP_KEYS}
    for name in all_row_names:
        d = divisions.get(name)
        if not d:
            continue
        for k in CR_ACTUAL_KEYS:
            actuals[k] += d["actuals"].get(k, 0.0)
        total_exp += d["total_exp"]
        for k in SWAP_KEYS:
            swap[k] += d["swap"].get(k, 0.0)
    swap["Total"] = sum(swap.values())
    ecr_with_pension = (actuals["Total"] / total_exp * 100) if total_exp > 0 else 0
    denom = total_exp - swap["Pension"]
    ecr_without_pension = (actuals["Total"] / denom * 100) if denom > 0 else 0
    return {
        "actuals": {k: round(v, 4) for k, v in actuals.items()},
        "total_exp": round(total_exp, 4),
        "swap": {k: round(v, 4) for k, v in swap.items()},
        "ecr_with_pension": round(ecr_with_pension, 4),
        "ecr_without_pension": round(ecr_without_pension, 4),
    }


def main():
    cfg = load_config()
    ecr_cfg = get_section(cfg, "ecr")
    known_divisions = ecr_cfg["known_divisions"]
    extra_rows = ecr_cfg["circle_full_extra_rows"]

    html = (BASE / "index.html").read_text(encoding="utf-8")
    apr_data = extract_data_by_month(html)
    office_entries = extract_office_entries(html)
    if set(office_entries) != set(extra_rows):
        sys.exit(f"ERROR: OFFICE_ENTRIES rows {sorted(office_entries)} != "
                  f"circle_full_extra_rows {sorted(extra_rows)}")

    # --- 1. data/targets.json ---
    targets = build_targets_json(apr_data, known_divisions)
    (DATA_DIR / "targets.json").write_text(
        json.dumps(targets, ensure_ascii=False, separators=(",", ":"), sort_keys=True),
        encoding="utf-8")
    print(f"Wrote data/targets.json ({len(targets)} divisions)")

    # --- 2. retrofit dataset_2026-04.json's ecr section ---
    ds_path = DATA_DIR / "dataset_2026-04.json"
    dataset = json.loads(ds_path.read_text(encoding="utf-8"))
    if "ecr" in dataset["sections"]:
        sys.exit("ERROR: dataset_2026-04.json already has an 'ecr' section — "
                  "this migration has already run. Aborting to avoid clobbering.")

    divisions = {}
    for name in known_divisions:
        rec = apr_data[name]
        divisions[name] = {
            "actuals": {k: round(v, 7) for k, v in rec["actuals"].items()},
            "total_exp": round(rec.get("total_exp", 0.0), 7),
            "swap": {k: round(v, 7) for k, v in rec.get("swap", {}).items()},
        }
    for name, fields in office_entries.items():
        divisions[name] = build_extra_row_division(fields)

    circle_full = build_circle_full(divisions, set(known_divisions) | set(extra_rows))
    ecr_section_data = {"divisions": divisions, "circle_full": circle_full}
    dataset["sections"]["ecr"] = {
        "standalone": ecr_section_data,
        "cumulative": ecr_section_data,  # cumulative_mode: source -> passthrough
        "row_count": len(divisions),
    }
    ds_path.write_text(json.dumps(dataset, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Retrofitted data/dataset_2026-04.json: ecr section, {len(divisions)} rows (expect row_count 39)")
    print("Sample (Guntur):", divisions.get("Guntur", {}).get("actuals"))


if __name__ == "__main__":
    main()
