#!/usr/bin/env python3
"""ci_build_sections.py — CI orchestration layer between drive_pull.py and
assemble.py. Given a month and a downloads/ directory (populated by
drive_pull.py), figures out which canonical files are actually present,
runs build_dataset.py's validate+extract for each, and — only if every
attempted section succeeds — runs assemble.py to refresh data/latest.json.

Never partially deploys: if ANY section fails validation, this exits
non-zero WITHOUT running assemble.py, so data/latest.json is left exactly
as it was — the GitHub Action must treat this exit code as "do not
deploy, last-known-good stays live."

Writes, for the calling workflow to consume:
  - $GITHUB_OUTPUT: success (true/false), error_count
  - $GITHUB_STEP_SUMMARY: a markdown report — circle totals + biggest
    movers on success, or the plain-language validation errors on
    failure. Visible in the Actions UI and GitHub's mobile app, so a
    staging approval can happen from a phone.
  - validation_errors.json: structured [{"section", "message"}, ...],
    consumed by the uploader-email step so it never has to re-parse logs.

Usage:
    python ci_build_sections.py --month 2026-07 --downloads downloads/
    python ci_build_sections.py --month 2026-07 --downloads downloads/ --only-section ecr
"""
import argparse
import json
import os
import sys
from pathlib import Path

# Windows consoles default to cp1252, which can't encode some characters
# used in summary text below — reconfigure rather than avoid Unicode
# entirely, since GITHUB_STEP_SUMMARY and other output should stay UTF-8.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pipeline.config import load_config
import build_dataset
import assemble as assemble_mod

BASE = Path(__file__).parent
DATA_DIR = BASE / "data"

# section -> (label, function(latest_dict) -> (metric_label, value, fmt))
_HEADLINE = {
    "ecr": lambda d: ("ECR revenue (circle, Cr)", (d.get("CIRCLE_FULL") or {}).get("actuals", {}).get("Total")),
    "posb": lambda d: ("POSB net addition (circle, latest month)", _posb_headline(d)),
    "pli": lambda d: ("PLI policies procured (circle, cumulative)",
                       (d.get("PLI_POLICIES", {}).get("__CUM__", {}).get("__CIRCLE__", {}) or {}).get("policies")),
    "rpli": lambda d: ("RPLI policies procured (circle, cumulative)",
                        (d.get("RPLI_POLICIES", {}).get("__CUM__", {}).get("__CIRCLE__", {}) or {}).get("policies")),
    "booking": lambda d: ("Booking articles (circle, cumulative)",
                           (d.get("BOOKING_BY_MONTH", {}).get("Cumulative", {}).get("circle", {})
                            .get("totals", {}) or {}).get("articles")),
}


def _posb_headline(d):
    by_month = d.get("POSB_BY_MONTH") or {}
    if not by_month:
        return None
    latest_label = sorted(by_month.keys())[-1]
    return by_month[latest_label].get("__CIRCLE__", {}).get("net")


def _find_downloaded(downloads_dir: Path, month_iso: str, cfg: dict) -> dict:
    month_dir = downloads_dir / month_iso
    out = {}
    for section_name, section_cfg in cfg["sections"].items():
        p = month_dir / section_cfg["canonical_filename"]
        out[section_name] = p if p.exists() else None
    return out


def _fmt(v):
    if v is None:
        return "n/a"
    if isinstance(v, float):
        return f"{v:,.2f}"
    return f"{v:,}"


def build_summary_markdown(month_iso: str, built_sections: list[str], new_data: dict, old_data: dict | None) -> str:
    lines = [f"## ✅ Data pipeline — {month_iso}", "", f"Rebuilt: {', '.join(built_sections)}", "", "| Metric | New | Previous | Change |", "|---|---|---|---|"]
    seen = set()
    for section in built_sections:
        key = "booking" if section == "booking" else section
        if key in seen or key not in _HEADLINE:
            continue
        seen.add(key)
        label, new_val = _HEADLINE[key](new_data)
        _, old_val = _HEADLINE[key](old_data) if old_data else (None, None)
        change = "n/a"
        if isinstance(new_val, (int, float)) and isinstance(old_val, (int, float)):
            delta = new_val - old_val
            change = f"{'+' if delta >= 0 else ''}{_fmt(delta)}"
        lines.append(f"| {label} | {_fmt(new_val)} | {_fmt(old_val)} | {change} |")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", required=True)
    ap.add_argument("--downloads", type=Path, required=True)
    ap.add_argument("--only-section", help="Restrict to one section (+ its booking sibling if applicable).")
    args = ap.parse_args()

    cfg = load_config()
    downloaded = _find_downloaded(args.downloads, args.month, cfg)

    if args.only_section:
        keep = {args.only_section}
        if args.only_section.startswith("booking_"):
            keep |= {"booking_productwise", "booking_booktypewise"}
        downloaded = {k: v for k, v in downloaded.items() if k in keep}

    all_errors = []
    built_sections = []

    for section_name in ("ecr", "posb", "pli", "rpli"):
        path = downloaded.get(section_name)
        if not path:
            continue
        exit_code, msgs = build_dataset.run(section_name, args.month, path)
        if exit_code != 0:
            all_errors += [{"section": section_name, "message": m} for m in msgs]
        else:
            built_sections.append(section_name)

    pw_path = downloaded.get("booking_productwise")
    bt_path = downloaded.get("booking_booktypewise")
    if pw_path:
        exit_code, msgs = build_dataset.run_booking(args.month, pw_path, bt_path)
        if exit_code != 0:
            all_errors += [{"section": "booking", "message": m} for m in msgs]
        else:
            built_sections.append("booking")

    summary_text = ""
    old_latest = None
    latest_path = DATA_DIR / "latest.json"
    if latest_path.exists():
        old_latest = json.loads(latest_path.read_text(encoding="utf-8"))

    if all_errors:
        lines = [f"## ❌ Data pipeline — {args.month} — validation failed ({len(all_errors)} error(s))", ""]
        for e in all_errors:
            lines.append(f"- **{e['section']}**: {e['message']}")
        lines.append("")
        lines.append("**data/latest.json was NOT updated — last-known-good stays live.**")
        summary_text = "\n".join(lines)
    elif built_sections:
        print(f"\nAll {len(built_sections)} section(s) built cleanly: {', '.join(built_sections)}")
        print("Running assemble.py...")
        result = assemble_mod.assemble()
        DATA_DIR.mkdir(exist_ok=True)
        latest_path.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"  Wrote {latest_path} ({latest_path.stat().st_size:,} bytes)")
        summary_text = build_summary_markdown(args.month, built_sections, result, old_latest)
    else:
        summary_text = (f"## Data pipeline — {args.month}\n\n"
                         f"No files found in `downloads/{args.month}/` — nothing to build this run.")

    print("\n" + summary_text)

    gh_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if gh_summary:
        with open(gh_summary, "a", encoding="utf-8") as f:
            f.write(summary_text + "\n")

    gh_output = os.environ.get("GITHUB_OUTPUT")
    if gh_output:
        with open(gh_output, "a", encoding="utf-8") as f:
            f.write(f"success={'false' if all_errors else 'true'}\n")
            f.write(f"error_count={len(all_errors)}\n")

    (BASE / "validation_errors.json").write_text(json.dumps(all_errors, ensure_ascii=False), encoding="utf-8")
    sys.exit(1 if all_errors else 0)


if __name__ == "__main__":
    main()
