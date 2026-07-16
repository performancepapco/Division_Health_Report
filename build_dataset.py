#!/usr/bin/env python3
"""build_dataset.py — generalized, config-driven replacement for the
per-month build_*.py scripts.

Processes ONE section for ONE month: validate -> extract -> merge with
stored cumulative -> write into data/dataset_<YYYY-MM>.json. Run assemble.py
afterward to rebuild data/latest.json (the *_BY_MONTH structures, derived
views, and cross-month rebuilds) from everything in data/dataset_*.json —
that assembly needs all months at once, so it isn't done here per-section.

On ANY validation failure: nothing is written, a plain-language error list
is printed, and the process exits non-zero — callers (the GitHub Action)
must not deploy on a non-zero exit. This intentionally mirrors the "never
deploy bad data" requirement from the pipeline spec.

Booking is special-cased: it's the one section that needs two files
(Product-wise + Book-type-wise) to produce one "booking" dataset entry —
see pipeline/sections/booking.py's module docstring.

Usage:
    python build_dataset.py --section ecr --month 2026-06 --input path/to/ECR.xlsx
    python build_dataset.py --section ecr --month 2026-06 --input path/to/ECR.xlsx --check-only
    python build_dataset.py --section booking --month 2026-06 \
        --input-productwise path/to/Booking_Productwise.csv \
        --input-booktypewise path/to/Booking_BookTypewise_Datewise.csv
"""
import argparse
import json
import sys
from pathlib import Path

from pipeline.config import load_config, get_section
from pipeline.common import validate_iso_month, prev_iso_month
from pipeline.validate import validate_row_count

BASE = Path(__file__).parent
DATA_DIR = BASE / "data"

# Registered section plugins. Sections not yet listed here raise a clear
# error below rather than failing silently or guessing.
_SECTION_MODULES = {}


def _load_section_module(name: str):
    if name in _SECTION_MODULES:
        return _SECTION_MODULES[name]
    import importlib
    try:
        mod = importlib.import_module(f"pipeline.sections.{name}")
    except ModuleNotFoundError:
        raise SystemExit(
            f"Section '{name}' has no pipeline/sections/{name}.py yet."
        )
    _SECTION_MODULES[name] = mod
    return mod


def _dataset_path(month_iso: str) -> Path:
    return DATA_DIR / f"dataset_{month_iso}.json"


def _load_dataset(month_iso: str) -> dict:
    p = _dataset_path(month_iso)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"month": month_iso, "sections": {}}


def _finish(section_name: str, month_iso: str, new_slice, mod, row_count_band) -> tuple[int, list[str]]:
    """Shared tail: row-count-band check, merge, write dataset + latest.json.
    Returns (exit_code, error_messages) — messages are plain-language and
    safe to relay to an uploader by email; empty on success."""
    new_count = mod.row_count(new_slice)

    prev_month = prev_iso_month(month_iso)
    prev_dataset = _load_dataset(prev_month)
    prev_section = prev_dataset["sections"].get(section_name)
    prev_cumulative = prev_section["cumulative"] if prev_section else None
    prev_count = mod.row_count(prev_cumulative) if prev_cumulative else None

    count_errors = validate_row_count(section_name, section_name, new_count, prev_count, row_count_band)
    if count_errors:
        msgs = [e.message for e in count_errors]
        print(f"\n{len(msgs)} validation error(s):")
        for m in msgs:
            print(f"  - {m}")
        return 1, msgs

    cumulative = mod.merge_cumulative(new_slice, prev_cumulative)

    dataset = _load_dataset(month_iso)
    dataset["sections"][section_name] = {
        "standalone": new_slice,
        "cumulative": cumulative,
        "row_count": new_count,
    }
    DATA_DIR.mkdir(exist_ok=True)
    _dataset_path(month_iso).write_text(
        json.dumps(dataset, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"  Wrote {_dataset_path(month_iso).relative_to(BASE)}")
    print("  Run assemble.py to refresh data/latest.json from all months on record.")
    return 0, []


def run(section_name: str, month_iso: str, input_path: Path, check_only: bool = False) -> tuple[int, list[str]]:
    """Returns (exit_code, error_messages) — see _finish()."""
    validate_iso_month(month_iso)
    cfg = load_config()
    section_cfg = get_section(cfg, section_name)
    mod = _load_section_module(section_name)

    print(f"[{section_name}] validating {input_path} for {month_iso}...")
    errors = mod.validate(section_cfg, input_path, month_iso)
    if errors:
        msgs = [e.message for e in errors]
        print(f"\n{len(msgs)} validation error(s):")
        for m in msgs:
            print(f"  - {m}")
        return 1, msgs
    print("  OK: headers and reporting month match.")

    if check_only:
        print("--check-only: not extracting or writing.")
        return 0, []

    print(f"[{section_name}] extracting...")
    new_slice = mod.extract(section_cfg, input_path, month_iso)
    return _finish(section_name, month_iso, new_slice, mod, section_cfg["row_count_band"])


def _find_prev_posb_silent(month_iso: str) -> tuple[dict | None, str | None]:
    """posb_silent's cumulative is a persistent snapshot, not a per-month
    activity slice — so unlike _finish()'s prev_iso_month() lookup (one
    calendar month back), this scans every dataset on record for the most
    recent posb_silent cumulative at or before month_iso. "At" (not just
    "before") matters: re-running the same month after it's already been
    committed must see its own prior result, so the monotonic as_of check
    in posb_silent.validate() can reject the duplicate. Skipping a month
    entirely (operator forgot to upload) is also handled correctly this
    way — offices just keep carrying forward from whenever they were last
    seen, however many months back that was.
    Returns (cumulative_dict_or_None, its_meta_as_of_or_None)."""
    months = sorted(p.stem.removeprefix("dataset_") for p in DATA_DIR.glob("dataset_*.json"))
    for month in reversed(months):
        if month > month_iso:
            continue
        section = _load_dataset(month)["sections"].get("posb_silent")
        if section and section.get("cumulative"):
            cum = section["cumulative"]
            return cum, (cum.get("_meta") or {}).get("as_of")
    return None, None


def run_posb_silent(month_iso: str, input_path: Path, check_only: bool = False) -> tuple[int, list[str]]:
    """Returns (exit_code, error_messages) — see _finish(). Special-cased
    (like run_booking) rather than going through run()/_finish(): this
    section's validation needs the currently-in-production as_of (for the
    monotonic guard) and its cumulative-merge needs a prev_cumulative
    sourced by _find_prev_posb_silent() rather than the generic
    prev_iso_month() lookup — see that function's docstring."""
    validate_iso_month(month_iso)
    cfg = load_config()
    section_cfg = get_section(cfg, "posb_silent")
    mod = _load_section_module("posb_silent")

    prev_cumulative, current_as_of = _find_prev_posb_silent(month_iso)

    print(f"[posb_silent] validating {input_path} for {month_iso}...")
    errors = mod.validate(section_cfg, input_path, month_iso, current_as_of)
    if errors:
        msgs = [e.message for e in errors]
        print(f"\n{len(msgs)} validation error(s):")
        for m in msgs:
            print(f"  - {m}")
        return 1, msgs
    print("  OK: schema, checksum, row count, and as_of_month all check out.")

    print("[posb_silent] extracting...")
    new_slice = mod.extract(section_cfg, input_path, month_iso)

    new_count = mod.row_count(new_slice)
    prev_count = mod.row_count(prev_cumulative) if prev_cumulative else None
    count_errors = validate_row_count("posb_silent", "posb_silent", new_count, prev_count, section_cfg["row_count_band"])
    if count_errors:
        msgs = [e.message for e in count_errors]
        print(f"\n{len(msgs)} validation error(s):")
        for m in msgs:
            print(f"  - {m}")
        return 1, msgs

    if check_only:
        diff = mod.diff_summary(new_slice, prev_cumulative)
        print("--check-only: dry-run diff (nothing written):")
        print(f"    {diff['added']:,} added, {diff['changed']:,} changed, "
              f"{diff['unchanged']:,} unchanged, {diff['carried_forward']:,} carried forward untouched")
        if diff["sample_changed"]:
            print(f"    sample changed codes: {diff['sample_changed']}")
        if diff["sample_added"]:
            print(f"    sample added codes: {diff['sample_added']}")
        return 0, []

    cumulative = mod.merge_cumulative(new_slice, prev_cumulative)

    dataset = _load_dataset(month_iso)
    dataset["sections"]["posb_silent"] = {
        "standalone": new_slice,
        "cumulative": cumulative,
        "row_count": new_count,
    }
    DATA_DIR.mkdir(exist_ok=True)
    _dataset_path(month_iso).write_text(
        json.dumps(dataset, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"  Wrote {_dataset_path(month_iso).relative_to(BASE)}")
    print("  Run assemble.py to refresh data/latest.json from all months on record.")
    return 0, []


def run_booking(month_iso: str, productwise_path: Path, booktypewise_path: Path | None,
                 check_only: bool = False) -> tuple[int, list[str]]:
    """Returns (exit_code, error_messages) — see _finish()."""
    validate_iso_month(month_iso)
    cfg = load_config()
    pw_cfg = get_section(cfg, "booking_productwise")
    bt_cfg = get_section(cfg, "booking_booktypewise")
    mod = _load_section_module("booking")

    print(f"[booking] validating Product-wise file {productwise_path} for {month_iso}...")
    errors = mod.validate_productwise(pw_cfg, productwise_path, month_iso)
    if booktypewise_path is not None:
        print(f"[booking] validating Book-type-wise file {booktypewise_path}...")
        errors += mod.validate_booktypewise(bt_cfg, booktypewise_path, month_iso)
    else:
        print("[booking] WARNING: no Book-type-wise file given — customer_mix will be all-zero.")

    if errors:
        msgs = [e.message for e in errors]
        print(f"\n{len(msgs)} validation error(s):")
        for m in msgs:
            print(f"  - {m}")
        return 1, msgs
    print("  OK: headers and reporting month match.")

    if check_only:
        print("--check-only: not extracting or writing.")
        return 0, []

    print("[booking] extracting...")
    new_slice = mod.extract(productwise_path, booktypewise_path, month_iso)
    # Booking's row-count band lives on booking_productwise's config (both
    # section entries share the same band value in pipeline_config.yaml).
    return _finish("booking", month_iso, new_slice, mod, pw_cfg["row_count_band"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--section", required=True)
    ap.add_argument("--month", required=True, help="YYYY-MM")
    ap.add_argument("--input", type=Path, help="Required for all sections except 'booking'.")
    ap.add_argument("--input-productwise", type=Path, help="'booking' section only.")
    ap.add_argument("--input-booktypewise", type=Path, help="'booking' section only, optional.")
    ap.add_argument("--check-only", action="store_true",
                     help="Run validation only, don't extract or write.")
    args = ap.parse_args()

    if args.section == "booking":
        if not args.input_productwise:
            raise SystemExit("--section booking requires --input-productwise (and optionally --input-booktypewise)")
        if not args.input_productwise.exists():
            raise SystemExit(f"Input file not found: {args.input_productwise}")
        if args.input_booktypewise and not args.input_booktypewise.exists():
            raise SystemExit(f"Input file not found: {args.input_booktypewise}")
        exit_code, _ = run_booking(args.month, args.input_productwise, args.input_booktypewise, args.check_only)
        sys.exit(exit_code)
    elif args.section == "posb_silent":
        if not args.input:
            raise SystemExit("--section posb_silent requires --input")
        if not args.input.exists():
            raise SystemExit(f"Input file not found: {args.input}")
        exit_code, _ = run_posb_silent(args.month, args.input, args.check_only)
        sys.exit(exit_code)
    else:
        if not args.input:
            raise SystemExit(f"--section {args.section} requires --input")
        if not args.input.exists():
            raise SystemExit(f"Input file not found: {args.input}")
        exit_code, _ = run(args.section, args.month, args.input, args.check_only)
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
