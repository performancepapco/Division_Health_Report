#!/usr/bin/env python3
"""drive_pull.py — downloads canonical section files from Google Drive
(DHCUploads/<YYYY-MM>/) for use by build_dataset.py.

Usage:
    # Pull one section's file (what the GitHub Action does for a
    # repository_dispatch triggered by a single upload):
    python drive_pull.py --month 2026-07 --section ecr --dest downloads/

    # Pull everything available for a month (daily cron / manual rebuild):
    python drive_pull.py --month 2026-07 --dest downloads/

Prints, for each section, either the local path it downloaded to or "not
uploaded yet" — a missing file is routine, not an error, so this exits 0
even if some/all sections are missing. It only exits non-zero if it
genuinely can't reach Drive (bad credentials, DHCUploads not shared).

Booking needs special handling downstream: this script downloads
Booking_Productwise.csv and Booking_BookTypewise.csv as two independent
sections (booking_productwise / booking_booktypewise), matching how the
Form/Apps Script treats them — build_dataset.py's `--section booking` path
then takes both resulting file paths together.
"""
import argparse
from pathlib import Path

from pipeline.config import load_config
from pipeline.common import validate_iso_month
from pipeline.drive import DriveClient, DriveError, download_section_file, download_month


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", required=True, help="YYYY-MM")
    ap.add_argument("--section", help="Download just this section's file. Omit to pull everything available.")
    ap.add_argument("--dest", type=Path, default=Path("downloads"))
    args = ap.parse_args()

    validate_iso_month(args.month)
    cfg = load_config()

    if args.section and args.section not in cfg["sections"]:
        raise SystemExit(f"Unknown section '{args.section}'. Known: {', '.join(cfg['sections'])}")

    try:
        client = DriveClient.from_env()
    except DriveError as e:
        raise SystemExit(f"ERROR: {e}")

    if args.section:
        try:
            path = download_section_file(client, args.month, args.section, args.dest, cfg)
        except DriveError as e:
            raise SystemExit(f"ERROR: {e}")
        if path:
            print(f"{args.section}: downloaded -> {path}")
        else:
            print(f"{args.section}: not uploaded yet for {args.month}")
        return

    try:
        results = download_month(client, args.month, args.dest, cfg)
    except DriveError as e:
        raise SystemExit(f"ERROR: {e}")

    for section_name, path in results.items():
        if path:
            print(f"{section_name}: downloaded -> {path}")
        else:
            print(f"{section_name}: not uploaded yet for {args.month}")


if __name__ == "__main__":
    main()
