#!/usr/bin/env python3
"""
patch_june2026_subdiv_bolookup.py
────────────────────────────────────
Replaces SUBDIV_DATA, BO_LOOKUP, BO_SEARCH with the rebuilt Apr+May+Jun 2026
cumulative snapshot from build_subdiv_bolookup_june2026.py.

Run:  python patch_june2026_subdiv_bolookup.py
"""
import json
from pathlib import Path

BASE = Path(__file__).parent
HTML = BASE / "index.html"

subdiv = json.loads((BASE / "_subdiv_data_june.json").read_text(encoding="utf-8"))
bolu = json.loads((BASE / "_bo_lookup_june.json").read_text(encoding="utf-8"))
bo_lookup, bo_search = bolu["lookup"], bolu["index"]


def replace_const(html, name, new_json):
    start = html.find(f"const {name} =")
    if start < 0:
        raise SystemExit(f"ERROR: const {name} not found")
    end = html.find(";\n", start) + 2
    new_decl = f"const {name} = {new_json};\n"
    return html[:start] + new_decl + html[end:]


def main():
    html = HTML.read_text(encoding="utf-8")
    print(f"Read index.html ({len(html):,} chars)")

    html = replace_const(html, "SUBDIV_DATA", json.dumps(subdiv, ensure_ascii=False, separators=(",", ":")))
    print("Replaced SUBDIV_DATA")
    html = replace_const(html, "BO_LOOKUP", json.dumps(bo_lookup, ensure_ascii=False, separators=(",", ":")))
    print("Replaced BO_LOOKUP")
    html = replace_const(html, "BO_SEARCH", json.dumps(bo_search, ensure_ascii=False, separators=(",", ":")))
    print("Replaced BO_SEARCH")

    HTML.write_text(html, encoding="utf-8")
    print(f"Wrote index.html ({len(html):,} chars)")


if __name__ == "__main__":
    main()
