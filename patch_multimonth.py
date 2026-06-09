"""
patch_multimonth.py
Implements multi-month DATA engine in index.html:
  - Wraps DATA into DATA_BY_MONTH["Apr-26"]
  - Adds live `let DATA = {}` alias refreshed on month change
  - Adds derivation helpers (subtract, pro-rata, rank recompute)
  - Wires onMonthChange and initial render to call refreshActiveData()
"""
import re

HTML = r"C:\Users\Bhargavi\Documents\Division_Health_Report\Division_Health_Report\index.html"

with open(HTML, encoding="utf-8") as f:
    src = f.read()

original_len = len(src)
changes = 0

# ── 1. Wrap DATA declaration ─────────────────────────────────────────────────
OLD1 = "const DATA = {"
NEW1 = 'const DATA_BY_MONTH = { "Apr-26": {'
if OLD1 in src:
    src = src.replace(OLD1, NEW1, 1)
    changes += 1
    print("1: DATA header → DATA_BY_MONTH[Apr-26] — OK")
else:
    print("1: FAIL — 'const DATA = {' not found")

# The DATA JSON line ends with: "region_size": N}};
# We need to close the DATA_BY_MONTH wrapper too: "region_size": N}} };
# Find the first occurrence of }}; on the DATA_BY_MONTH line
data_end_pat = re.compile(r'"region_size": \d+\}\};')
m = data_end_pat.search(src)
if m:
    src = src[:m.end()-2] + "} };" + src[m.end():]
    changes += 1
    print("2: DATA JSON closing brace wrapped — OK")
else:
    print("2: FAIL — could not find DATA JSON end pattern")

# ── 3. Add let DATA = {}; before CIRCLE constant ─────────────────────────────
OLD3 = "const CIRCLE = {"
NEW3 = "let DATA = {};\nconst CIRCLE = {"
if OLD3 in src:
    src = src.replace(OLD3, NEW3, 1)
    changes += 1
    print("3: let DATA = {}; added — OK")
else:
    print("3: FAIL — 'const CIRCLE = {' not found")

# ── 4. PLI_RPLI_PATCH: use DATA_BY_MONTH['Apr-26'] ──────────────────────────
OLD4 = (
    "Object.entries(PLI_RPLI_PATCH).forEach(([div, v]) => {\n"
    "  if (!DATA[div]) return;\n"
    "  if (DATA[div].pli)  DATA[div].pli.tbp_ach  = v.pli;\n"
    "  if (DATA[div].rpli) DATA[div].rpli.tbp_ach = v.rpli;\n"
    "});"
)
NEW4 = (
    "Object.entries(PLI_RPLI_PATCH).forEach(([div, v]) => {\n"
    "  const _apr = DATA_BY_MONTH['Apr-26'];\n"
    "  if (!_apr[div]) return;\n"
    "  if (_apr[div].pli)  _apr[div].pli.tbp_ach  = v.pli;\n"
    "  if (_apr[div].rpli) _apr[div].rpli.tbp_ach = v.rpli;\n"
    "});"
)
if OLD4 in src:
    src = src.replace(OLD4, NEW4, 1)
    changes += 1
    print("4: PLI_RPLI_PATCH → DATA_BY_MONTH — OK")
else:
    print("4: FAIL — PLI_RPLI_PATCH block not found")

# ── 5. OFFICE_ENTRIES loop: write into DATA_BY_MONTH['Apr-26'] ───────────────
OLD5 = "  DATA[name] = {"
NEW5 = "  DATA_BY_MONTH['Apr-26'][name] = {"
if OLD5 in src:
    src = src.replace(OLD5, NEW5, 1)
    changes += 1
    print("5: OFFICE_ENTRIES DATA[name] → DATA_BY_MONTH['Apr-26'][name] — OK")
else:
    print("5: FAIL — 'DATA[name] = {' not found")

# ── 6. Add multi-month helper functions ──────────────────────────────────────
MONTH_HELPERS = r"""
// ============ MULTI-MONTH DATA ENGINE ============
const MONTH_ORDER = ['Apr-26','May-26','Jun-26','Jul-26','Aug-26','Sep-26','Oct-26','Nov-26','Dec-26','Jan-27','Feb-27','Mar-27'];

function refreshActiveData() {
  DATA = getViewData();
  recomputeRanks();
}

function getViewData() {
  const from = document.getElementById('month-from').value;
  const to   = document.getElementById('month-to').value;
  const fromIdx = MONTH_ORDER.indexOf(from);
  const toIdx   = MONTH_ORDER.indexOf(to);
  if (from === to) return deriveMonthSnapshot(to);
  const numMonths = Math.max(1, toIdx - fromIdx + 1);
  return applyProRata(DATA_BY_MONTH[to] || DATA_BY_MONTH[from] || {}, numMonths);
}

function applyProRata(snapshot, numMonths) {
  const out = {};
  Object.entries(snapshot).forEach(([k, d]) => {
    if (!d || d.isAggregate) { out[k] = d; return; }
    const tgt = d.targets || {};
    const act = d.actuals || {};
    const pr  = {};
    ['Parcel','Mail Operations','IR & GB','CCS','POSB','PLI/RPLI','Total'].forEach(v => {
      pr[v] = (tgt[v] || 0) * numMonths / 12;
    });
    out[k] = { ...d, pro_rata: pr, ...recalcDerived(act, pr, d.total_exp || 0, d.swap ? d.swap.Pension || 0 : 0) };
  });
  return out;
}

function deriveMonthSnapshot(month) {
  const cur = DATA_BY_MONTH[month];
  if (!cur) {
    const fallback = MONTH_ORDER.slice().reverse().find(m => DATA_BY_MONTH[m]);
    return fallback ? applyProRata(DATA_BY_MONTH[fallback], 1) : {};
  }
  const idx = MONTH_ORDER.indexOf(month);
  if (idx <= 0) return applyProRata(cur, 1);
  const prevMonth = MONTH_ORDER[idx - 1];
  const prev = DATA_BY_MONTH[prevMonth];
  if (!prev) return applyProRata(cur, 1);
  const out = {};
  Object.keys(cur).forEach(function(divName) {
    const c = cur[divName], p = prev[divName];
    if (!c || c.isAggregate) { out[divName] = c; return; }
    out[divName] = subtractDivSnapshot(c, p);
  });
  return out;
}

function subtractDivSnapshot(c, p) {
  const act  = subObj(c.actuals,  p ? p.actuals  : null);
  const sw   = subObj(c.swap,     p ? p.swap     : null);
  const tgt  = c.targets;
  const pr   = calcProRata(tgt, 1);
  const exp  = (c.total_exp || 0) - (p ? (p.total_exp || 0) : 0);
  const pen  = sw ? (sw.Pension || 0) : 0;
  var pli  = c.pli;
  if (c.pli && p && p.pli) {
    pli = Object.assign({}, c.pli, {
      tbp_ach: (c.pli.tbp_ach || 0) - (p.pli.tbp_ach || 0),
      nbp_ach: (c.pli.nbp_ach || 0) - (p.pli.nbp_ach || 0),
      tbp_pro: (c.pli.tbp_target || 0) / 12
    });
  }
  var rpli = c.rpli;
  if (c.rpli && p && p.rpli) {
    rpli = Object.assign({}, c.rpli, {
      tbp_ach: (c.rpli.tbp_ach || 0) - (p.rpli.tbp_ach || 0),
      nbp_ach: (c.rpli.nbp_ach || 0) - (p.rpli.nbp_ach || 0),
      tbp_pro: (c.rpli.tbp_target || 0) / 12
    });
  }
  var bk = c.booking;
  if (c.booking) {
    var bc = c.booking, bp = (p && p.booking) ? p.booking : {};
    bk = Object.assign({}, bc, {
      total_business_cr: (bc.total_business_cr || 0) - (bp.total_business_cr || 0),
      total_articles:    (bc.total_articles    || 0) - (bp.total_articles    || 0),
      wi_arts:           (bc.wi_arts           || 0) - (bp.wi_arts           || 0),
      bnpl_arts:         (bc.bnpl_arts         || 0) - (bp.bnpl_arts         || 0)
    });
    var tot = bk.total_articles || 0;
    bk.wi_share   = tot > 0 ? bk.wi_arts   / tot * 100 : 0;
    bk.bnpl_share = tot > 0 ? bk.bnpl_arts / tot * 100 : 0;
  }
  return Object.assign({}, c, {
    actuals: act, targets: tgt, pro_rata: pr, total_exp: exp, swap: sw, pli: pli, rpli: rpli, booking: bk
  }, recalcDerived(act, pr, exp, pen));
}

function calcProRata(tgt, n) {
  var pr = {};
  if (tgt) Object.keys(tgt).forEach(function(k) { pr[k] = (tgt[k] || 0) * n / 12; });
  return pr;
}

function recalcDerived(act, pr, exp, pen) {
  var att = {};
  ['Parcel','Mail Operations','IR & GB','CCS','POSB','PLI/RPLI'].forEach(function(v) {
    att[v] = (pr && pr[v] > 0) ? ((act ? (act[v] || 0) : 0) / pr[v] * 100) : 0;
  });
  var rev = act ? (act.Total || 0) : 0;
  return {
    attainments:         att,
    composite_score:     (pr && pr.Total > 0) ? rev / pr.Total * 100 : 0,
    ecr_with_pension:    exp > 0              ? rev / exp * 100       : 0,
    ecr_without_pension: (exp - pen) > 0      ? rev / (exp-pen) * 100 : 0
  };
}

function subObj(c, p) {
  if (!c) return null;
  if (!p) return Object.assign({}, c);
  var r = {};
  Object.keys(c).forEach(function(k) {
    r[k] = (typeof c[k] === 'number') ? ((c[k] || 0) - (p[k] || 0)) : c[k];
  });
  return r;
}

function recomputeRanks() {
  var all = Object.entries(DATA).filter(function(e) { return e[1] && !e[1].isOffice && !e[1].isAggregate; });
  all.sort(function(a, b) { return (b[1].composite_score || 0) - (a[1].composite_score || 0); });
  all.forEach(function(e, i) { DATA[e[0]].rank = i + 1; });
  ['Vijayawada','Visakhapatnam','Kurnool'].forEach(function(reg) {
    var rd = all.filter(function(e) { return e[1].region === reg; });
    rd.sort(function(a, b) { return (b[1].composite_score || 0) - (a[1].composite_score || 0); });
    rd.forEach(function(e, i) { e[1].rank_in_region = i + 1; e[1].region_size = rd.length; });
  });
}
// ============ END MULTI-MONTH DATA ENGINE ============

"""

OLD6 = "function showTab(t, btn) {"
NEW6 = MONTH_HELPERS + "function showTab(t, btn) {"
if OLD6 in src:
    src = src.replace(OLD6, NEW6, 1)
    changes += 1
    print("6: multi-month helpers added — OK")
else:
    print("6: FAIL — 'function showTab' not found")

# ── 7. onMonthChange: add refreshActiveData() ────────────────────────────────
OLD7 = (
    "function onMonthChange() {\n"
    "  const from = document.getElementById('month-from').value;\n"
    "  const to   = document.getElementById('month-to').value;\n"
    "  if (from === to) {\n"
    "    CUR_MONTH_LABEL = from;\n"
    "  } else {\n"
    "    CUR_MONTH_LABEL = from + ' to ' + to;\n"
    "  }\n"
    "  renderDivision(CUR_DIV_NAME);\n"
    "}"
)
NEW7 = (
    "function onMonthChange() {\n"
    "  const from = document.getElementById('month-from').value;\n"
    "  const to   = document.getElementById('month-to').value;\n"
    "  if (from === to) {\n"
    "    CUR_MONTH_LABEL = from;\n"
    "  } else {\n"
    "    CUR_MONTH_LABEL = from + ' to ' + to;\n"
    "  }\n"
    "  refreshActiveData();\n"
    "  renderDivision(CUR_DIV_NAME);\n"
    "}"
)
if OLD7 in src:
    src = src.replace(OLD7, NEW7, 1)
    changes += 1
    print("7: onMonthChange → refreshActiveData() — OK")
else:
    print("7: FAIL — onMonthChange block not found")

# ── 8. Initial render: refreshActiveData() before renderDivision ─────────────
OLD8 = "// Initial render\nrenderDivision"
NEW8 = "// Initial render\nrefreshActiveData();\nrenderDivision"
if OLD8 in src:
    src = src.replace(OLD8, NEW8, 1)
    changes += 1
    print("8: initial refreshActiveData() — OK")
else:
    print("8: FAIL — '// Initial render' not found")

print(f"\nTotal changes applied: {changes}/8")
print(f"File size: {len(src):,} chars (was {original_len:,}, delta +{len(src)-original_len:,})")

with open(HTML, "w", encoding="utf-8") as f:
    f.write(src)
print("File written.")
