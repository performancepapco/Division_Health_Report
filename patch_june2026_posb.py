#!/usr/bin/env python3
"""
patch_june2026_posb.py
────────────────────────
Replaces the old flat POSB_ACTUALS + POSB_RAW_JS (a single Apr+May-labeled
snapshot) with POSB_BY_MONTH = {"Apr-26":{...}, "May-26":{...}, "Jun-26":{...}}
holding true standalone-month data. renderPOSBTab / getPOSBData / getPOSBRawJS
(already patched into index.html) read from POSB_BY_MONTH directly.

Run:  python patch_june2026_posb.py
"""
import json
from pathlib import Path

BASE = Path(__file__).parent
HTML = BASE / "index.html"

posb_by_month = json.loads((BASE / "_posb_by_month.json").read_text(encoding="utf-8"))


def main():
    html = HTML.read_text(encoding="utf-8")
    print(f"Read index.html ({len(html):,} chars)")

    start = html.find("const POSB_ACTUALS")
    if start < 0:
        raise SystemExit("ERROR: const POSB_ACTUALS not found (already patched?)")
    raw_js_start = html.find("const POSB_RAW_JS", start)
    if raw_js_start < 0:
        raise SystemExit("ERROR: const POSB_RAW_JS not found")
    end = html.find(";\n", raw_js_start) + 2

    new_const = "const POSB_BY_MONTH = " + json.dumps(posb_by_month, ensure_ascii=False) + ";\n"
    html = html[:start] + new_const + html[end:]

    HTML.write_text(html, encoding="utf-8")
    print(f"Replaced POSB_ACTUALS/POSB_RAW_JS with POSB_BY_MONTH ({len(html):,} chars)")


if __name__ == "__main__":
    main()
