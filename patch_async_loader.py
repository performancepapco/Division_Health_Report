#!/usr/bin/env python3
"""patch_async_loader.py — one-time migration: converts index.html's baked-in
data constants to an async fetch('data/latest.json') loader.

Converts these from `const NAME = {huge literal};` to `let NAME = {};`
(empty placeholder, populated after the fetch resolves):
  POSB_BY_MONTH, PLI_POLICIES, RPLI_POLICIES, BOOKING_BY_MONTH, BO_LOOKUP,
  BO_SEARCH, SUBDIV_DATA, OFFICE_STATUS_BY_MONTH, SUBDIV_BOOKING, CIRCLE_FULL

Everything else — OFFICE_ENTRIES, PLI_RPLI_PATCH, the Apr-26 DATA_BY_MONTH
skeleton construction, MONTH_ORDER, REG_ABBR, targets — stays untouched.
Those are hand-authored target data, not tied to monthly branch uploads;
see pipeline/derive/ module docstrings for why each derived view was
in-scope and these weren't.

Also replaces the two hardcoded ECR May-26/Jun-26 patch IIFEs with a
single reusable function (applyEcrMonth) invoked in a loop over whatever
months the fetched data actually contains, so a July 2026 upload works
without another code change here.

Boundary-finding uses the same "find the first closing '};' after the
declaration" approach the codebase's own legacy patch_*.py scripts already
relied on (e.g. patch_june2026_circle_full.py) — safe here because none of
these values are strings containing literal "};"/"];" sequences.

Run:  python patch_async_loader.py [--target path/to/index.html]
"""
import argparse
import re
from pathlib import Path

BASE = Path(__file__).parent

# name -> ('object'|'array', declaration keyword to look for)
OBJECT_CONSTS = [
    "POSB_BY_MONTH", "PLI_POLICIES", "RPLI_POLICIES", "BOOKING_BY_MONTH",
    "BO_LOOKUP", "SUBDIV_DATA", "OFFICE_STATUS_BY_MONTH", "SUBDIV_BOOKING",
    "CIRCLE_FULL",
]
ARRAY_CONSTS = ["BO_SEARCH"]


def _find_decl_end(html: str, name: str, close_char: str) -> tuple[int, int]:
    """Returns (decl_start, value_end) for `const NAME = <value>;` — the
    first 'const NAME' occurrence, then the first close_char+';' after it."""
    m = re.search(rf"\bconst\s+{re.escape(name)}\s*=\s*", html)
    if not m:
        raise SystemExit(f"ERROR: 'const {name}' not found — already patched, or file changed?")
    decl_start = m.start()
    value_start = m.end()
    close = html.find(close_char + ";", value_start)
    if close < 0:
        raise SystemExit(f"ERROR: no closing '{close_char};' found for {name}")
    return decl_start, close + 2  # include the ';'


def replace_with_placeholder(html: str, name: str, empty_literal: str, close_char: str) -> str:
    start, end = _find_decl_end(html, name, close_char)
    replacement = f"let {name} = {empty_literal};"
    return html[:start] + replacement + html[end:]


ECR_PATCH_FN = """
// === ECR month patcher (generalized, replaces hardcoded May/Jun IIFEs) ===
// Applies ECR_BY_MONTH[label] (fetched) onto DATA_BY_MONTH, cloning forward
// from the previous month in MONTH_ORDER first if this month doesn't exist
// yet — so a new month (July 2026 onward) works with no further code
// changes here. April is skipped deliberately: its actuals are baked into
// OFFICE_ENTRIES (hand-authored, alongside targets), not fetched.
function applyEcrMonth(label, ecrDivisions) {
  if (!ecrDivisions) return;
  var idx = MONTH_ORDER.indexOf(label);
  if (idx <= 0) return; // Apr-26 (idx 0) or unknown label — skip
  if (!DATA_BY_MONTH[label]) {
    var prevLabel = MONTH_ORDER[idx - 1];
    if (!DATA_BY_MONTH[prevLabel]) return; // previous month never materialized
    DATA_BY_MONTH[label] = JSON.parse(JSON.stringify(DATA_BY_MONTH[prevLabel]));
  }
  Object.keys(ecrDivisions).forEach(function(k) {
    var d = DATA_BY_MONTH[label][k];
    if (!d) return;
    var e = ecrDivisions[k];
    d.actuals   = e.actuals;
    d.total_exp = e.total_exp;
    d.swap      = e.swap;
  });
}
function applyAllEcrMonths(ecrByMonth) {
  MONTH_ORDER.forEach(function(label) { applyEcrMonth(label, ecrByMonth[label]); });
}
// === END ECR month patcher ===
"""


def replace_ecr_patches(html: str) -> str:
    start_marker = "// === ECR May-26 cumulative financials (auto-generated) ==="
    end_marker = "// === END ECR Jun-26 ==="
    start = html.find(start_marker)
    end = html.find(end_marker)
    if start < 0 or end < 0:
        raise SystemExit("ERROR: ECR May/Jun patch markers not found — already patched, or file changed?")
    end += len(end_marker)
    return html[:start] + ECR_PATCH_FN.strip("\n") + html[end:]


LOADER_JS = """
// === ASYNC DATA LOADER (Phase 2) ===
// Fetches data/latest.json (assembled by assemble.py from every month's
// data/dataset_<YYYY-MM>.json) and populates the *_BY_MONTH / derived-view
// globals that used to be baked into this file as literals. Gates the
// first render until the fetch resolves — nothing above this point in the
// script relies on these globals being populated synchronously anymore.
async function loadDashboardData() {
  var url = 'data/latest.json?v=' + Date.now();
  var resp = await fetch(url);
  if (!resp.ok) throw new Error('Failed to load data/latest.json: HTTP ' + resp.status);
  var data = await resp.json();

  POSB_BY_MONTH          = data.POSB_BY_MONTH || {};
  PLI_POLICIES           = data.PLI_POLICIES || {};
  RPLI_POLICIES          = data.RPLI_POLICIES || {};
  BOOKING_BY_MONTH       = data.BOOKING_BY_MONTH || {};
  BO_LOOKUP              = data.BO_LOOKUP || {};
  BO_SEARCH              = data.BO_SEARCH || [];
  SUBDIV_DATA            = data.SUBDIV_DATA || {};
  OFFICE_STATUS_BY_MONTH = data.OFFICE_STATUS_BY_MONTH || {};
  SUBDIV_BOOKING         = data.SUBDIV_BOOKING || {};
  if (data.CIRCLE_FULL) CIRCLE_FULL = data.CIRCLE_FULL;

  applyAllEcrMonths(data.ECR_BY_MONTH || {});
}

loadDashboardData().then(function() {
  if (typeof onMonthChange === 'function') {
    onMonthChange();
  } else {
    refreshActiveData();
    renderDivision('__CIRCLE__');
  }
}).catch(function(err) {
  console.error('[Loader] Failed to load dashboard data:', err);
  var body = document.body;
  if (body) {
    var el = document.createElement('div');
    el.style.cssText = 'padding:24px;font-family:sans-serif;color:#900;background:#fee;border:1px solid #900;margin:16px;';
    el.textContent = 'Failed to load dashboard data (data/latest.json). ' +
      'If you are running this locally, serve it over HTTP (e.g. python -m http.server) ' +
      'rather than opening the file directly. Error: ' + err.message;
    body.prepend(el);
  }
});
// === END ASYNC DATA LOADER ===
"""


def replace_initial_render(html: str) -> str:
    old = """// Initial render — call onMonthChange so CUR_MONTH_LABEL syncs with the dropdowns,
// then renderDivision is invoked from inside it.
if (typeof onMonthChange === 'function') {
  onMonthChange();
} else {
  refreshActiveData();
  renderDivision('__CIRCLE__');
}"""
    if old not in html:
        raise SystemExit("ERROR: initial-render block not found verbatim — already patched, or file changed?")
    return html.replace(old, LOADER_JS.strip("\n"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=Path, default=BASE / "index.html")
    args = ap.parse_args()

    html = args.target.read_text(encoding="utf-8")
    print(f"Read {args.target} ({len(html):,} chars)")

    for name in OBJECT_CONSTS:
        html = replace_with_placeholder(html, name, "{}", "}")
        print(f"  {name} -> let {name} = {{}};")

    for name in ARRAY_CONSTS:
        html = replace_with_placeholder(html, name, "[]", "]")
        print(f"  {name} -> let {name} = [];")

    html = replace_ecr_patches(html)
    print("  Replaced ECR May/Jun patch IIFEs with generalized applyEcrMonth/applyAllEcrMonths")

    html = replace_initial_render(html)
    print("  Replaced synchronous initial render with async loadDashboardData() bootstrap")

    args.target.write_text(html, encoding="utf-8")
    print(f"\nWrote {args.target} ({len(html):,} chars)")


if __name__ == "__main__":
    main()
