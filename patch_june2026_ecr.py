#!/usr/bin/env python3
"""
patch_june2026_ecr.py
───────────────────────
Clones DATA_BY_MONTH['May-26'] into DATA_BY_MONTH['Jun-26'] (same targets,
mmu, pli/rpli sub-objects, posb_hist/posb_tgt, rank, region_size — these are
either annual constants or not yet re-sourced for June) and overwrites
actuals/total_exp/swap with the June ECR cumulative (Apr+May+Jun) figures,
mirroring what patch_ecr_may2026.py did for May.

Run:  python patch_june2026_ecr.py
"""
import json, re
from pathlib import Path

BASE = Path(__file__).parent
HTML = BASE / "index.html"

ecr_jun = json.loads((BASE / "_ecr_june2026.json").read_text(encoding="utf-8"))

MARK_B = "// === ECR Jun-26 cumulative financials (auto-generated) ==="
MARK_E = "// === END ECR Jun-26 ==="


def build_injection():
    js = (
        f"\n{MARK_B}\n"
        "(function(){\n"
        "  if (!DATA_BY_MONTH || !DATA_BY_MONTH['May-26']) return;\n"
        "  DATA_BY_MONTH['Jun-26'] = JSON.parse(JSON.stringify(DATA_BY_MONTH['May-26']));\n"
        "  var ECR_JUN = " + json.dumps(ecr_jun, ensure_ascii=False) + ";\n"
        "  Object.keys(ECR_JUN).forEach(function(k) {\n"
        "    var d = DATA_BY_MONTH['Jun-26'][k];\n"
        "    if (!d) return;\n"
        "    var e = ECR_JUN[k];\n"
        "    d.actuals   = e.actuals;\n"
        "    d.total_exp = e.total_exp;\n"
        "    d.swap      = e.swap;\n"
        "  });\n"
        "})();\n"
        f"{MARK_E}\n"
    )
    return js


def main():
    html = HTML.read_text(encoding="utf-8")
    print(f"Read index.html ({len(html):,} chars)")

    injection = build_injection()

    if MARK_B in html:
        pat = re.compile(re.escape(MARK_B) + r".*?" + re.escape(MARK_E) + r"\n", re.DOTALL)
        html, n = pat.subn(lambda _m: injection.lstrip("\n"), html, count=1)
        print(f"Replaced existing injection ({n} occurrence)")
    else:
        anchor = "// === END ECR May-26 ==="
        idx = html.find(anchor)
        if idx < 0:
            raise SystemExit("ERROR: could not find May-26 ECR injection marker; run patch_ecr_may2026.py first")
        insert_at = idx + len(anchor) + 1  # past the trailing newline
        html = html[:insert_at] + injection.lstrip("\n") + html[insert_at:]
        print("Inserted new Jun-26 DATA_BY_MONTH injection after ECR May-26 block")

    HTML.write_text(html, encoding="utf-8")
    print(f"Wrote index.html ({len(html):,} chars)")


if __name__ == "__main__":
    main()
