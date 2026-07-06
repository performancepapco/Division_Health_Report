#!/usr/bin/env python3
"""
patch_june2026_pli.py
──────────────────────
Injects Jun-26 standalone data + __CUM__ (Apr-to-Jun exact cumulative) into
PLI_POLICIES / RPLI_POLICIES via an idempotent Object.assign patch appended
right after each const declaration.

Run:  python patch_june2026_pli.py
"""
import json, re
from pathlib import Path

BASE = Path(__file__).parent
HTML = BASE / "index.html"

by_month = json.loads((BASE / "_pli_rpli_by_month.json").read_text(encoding="utf-8"))
cumulative = json.loads((BASE / "_pli_rpli_cumulative.json").read_text(encoding="utf-8"))

MARK_B = "// === PLI/RPLI Jun-26 + cumulative (auto-generated) ==="
MARK_E = "// === END PLI/RPLI Jun-26 ==="


def build_injection():
    pli_jun = json.dumps(by_month["pli"]["Jun-26"], ensure_ascii=False)
    rpli_jun = json.dumps(by_month["rpli"]["Jun-26"], ensure_ascii=False)
    pli_cum = json.dumps(cumulative["pli"], ensure_ascii=False)
    rpli_cum = json.dumps(cumulative["rpli"], ensure_ascii=False)
    return (
        f"\n{MARK_B}\n"
        f"Object.assign(PLI_POLICIES, {{'Jun-26': {pli_jun}}});\n"
        f"Object.assign(RPLI_POLICIES, {{'Jun-26': {rpli_jun}}});\n"
        f"PLI_POLICIES.__CUM__ = {pli_cum};\n"
        f"RPLI_POLICIES.__CUM__ = {rpli_cum};\n"
        f"{MARK_E}\n"
    )


def main():
    html = HTML.read_text(encoding="utf-8")
    print(f"Read index.html ({len(html):,} chars)")

    injection = build_injection()

    if MARK_B in html:
        pat = re.compile(re.escape(MARK_B) + r".*?" + re.escape(MARK_E) + r"\n", re.DOTALL)
        html, n = pat.subn(lambda _m: injection.lstrip("\n"), html, count=1)
        print(f"Replaced existing injection ({n} occurrence)")
    else:
        anchor = "const RPLI_POLICIES"
        idx = html.find(anchor)
        if idx < 0:
            raise SystemExit("ERROR: RPLI_POLICIES anchor not found")
        end = html.find("\n", idx) + 1
        html = html[:end] + injection.lstrip("\n") + html[end:]
        print("Inserted new injection after RPLI_POLICIES declaration")

    HTML.write_text(html, encoding="utf-8")
    print(f"Wrote index.html ({len(html):,} chars)")


if __name__ == "__main__":
    main()
