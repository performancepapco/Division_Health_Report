#!/usr/bin/env python3
"""render_error_email.py — turns validation_errors.json (written by
ci_build_sections.py) into a plain-language email body for the uploader.
No stack traces, no internal jargon — just section, month, and the exact
problem, matching the pipeline spec's uploader-facing error requirement.

Usage: python render_error_email.py --month 2026-07 --out email_body.txt
"""
import argparse
import json
from pathlib import Path

BASE = Path(__file__).parent


def render(month_iso: str, errors: list[dict]) -> str:
    lines = [
        f"The file you uploaded for the Division Health Card dashboard "
        f"({month_iso}) could not be processed:",
        "",
    ]
    for e in errors:
        lines.append(f"- {e['message']}")
    lines += [
        "",
        "Please fix the issue and re-upload using the template from /templates "
        "in the repository. The dashboard has not changed — last month's data "
        "is still showing.",
        "",
        "If you're not sure what's wrong, forward this email to the dashboard admin.",
    ]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", required=True)
    ap.add_argument("--errors-file", type=Path, default=BASE / "validation_errors.json")
    ap.add_argument("--out", type=Path, default=BASE / "email_body.txt")
    args = ap.parse_args()

    errors = json.loads(args.errors_file.read_text(encoding="utf-8")) if args.errors_file.exists() else []
    body = render(args.month, errors)
    args.out.write_text(body, encoding="utf-8")
    print(body)


if __name__ == "__main__":
    main()
