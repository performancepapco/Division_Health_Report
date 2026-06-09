#!/usr/bin/env python3
"""
patch_booking_months.py
───────────────────────
Builds month-keyed booking data (Apr-26 / May-26 / Cumulative) from the
clean per-month CSVs (Apr 1-30 from uploads/april_2026/, May 1-31 from
uploads/may_2026/), aggregated to Circle / Region / Division scopes.

Then patches index.html to:
  - Inject BOOKING_BY_MONTH constant
  - Add a CUR_BOOKING_MONTH global and an in-tab month switcher
  - Make pickBookingSlice read from BOOKING_BY_MONTH[CUR_BOOKING_MONTH]
    so the Booking tab's daily trend, peak day, product mix, top-25, etc.
    follow the user's month choice
"""

import re, json, csv
from pathlib import Path
from collections import defaultdict
from datetime import datetime

BASE = Path(__file__).parent
HTML = BASE / "index.html"
UP   = BASE / "uploads"
HIER = BASE / "office_hierarchy.json"

APR_PROD = UP / "april_2026" / "Booking_Productwise_Report apr 2026.csv"
APR_BOOK = UP / "april_2026" / "Booking_BookTypewise_Datewise_Report apr 2026.csv"
MAY_PROD = UP / "may_2026"   / "Booking_Productwise_Report (2).csv"
MAY_BOOK = UP / "may_2026"   / "Booking_BookTypewise_Datewise_Report (1).csv"

CR = 10_000_000
L  = 100_000


def short_div(s):
    return re.sub(r"\s+Division\s*$", "", str(s)).strip() if s else ""


def short_region(s):
    return str(s).replace(" Region", "").strip() if s else ""


def load_hierarchy():
    with open(HIER, encoding="utf-8") as f:
        h = json.load(f)
    # normalize: oid_str -> {division, region, name, type}
    out = {}
    for k, v in h.items():
        out[str(k)] = {
            "division": short_div(v.get("division", "")),
            "region":   short_region(v.get("region", "")),
            "name":     v.get("name", ""),
            "type":     v.get("type", ""),
        }
    return out


def read_productwise(path):
    """
    Returns:
      by_office[oid] = {name, articles, business, products: set(), daily: {date: {arts, biz}}, prod_per_office: {pname: {arts, biz}}}
      products_global: {pname: {articles, business, offices: set()}}
      daily_global:    {date: {articles, business}}
    """
    by_off = defaultdict(lambda: {
        "name": None, "articles": 0, "business": 0.0,
        "products": set(),
        "daily": defaultdict(lambda: {"articles": 0, "business": 0.0}),
        "by_prod": defaultdict(lambda: {"articles": 0, "business": 0.0}),
    })
    prods = defaultdict(lambda: {"articles": 0, "business": 0.0, "offices": set()})
    daily = defaultdict(lambda: {"articles": 0, "business": 0.0})

    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            oid = (row.get("office-id") or "").strip()
            if not oid or oid == "-":
                continue
            oname = (row.get("office-name") or "").strip()
            date  = (row.get("booking-date") or "")[:10]
            pname = (row.get("product-name") or "").strip()
            arts  = int(row.get("article-count") or 0)
            amt   = float(row.get("total_amount") or 0)
            if not pname or not date:
                continue

            rec = by_off[oid]
            if rec["name"] is None: rec["name"] = oname
            rec["articles"] += arts
            rec["business"] += amt
            rec["products"].add(pname)
            rec["daily"][date]["articles"] += arts
            rec["daily"][date]["business"] += amt
            rec["by_prod"][pname]["articles"] += arts
            rec["by_prod"][pname]["business"] += amt

            prods[pname]["articles"] += arts
            prods[pname]["business"] += amt
            prods[pname]["offices"].add(oid)
            daily[date]["articles"] += arts
            daily[date]["business"] += amt

    return by_off, prods, daily


def read_booktypewise(path):
    """Returns by_off[oid] = {walk_in, bulk_bnpl, postal_service, commercial, other}."""
    out = defaultdict(lambda: {"walk_in": 0, "bulk_bnpl": 0, "postal_service": 0,
                                "commercial": 0, "other": 0})
    if not path.exists():
        print(f"  WARN: {path.name} missing")
        return out
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            oid = (row.get("Office ID") or "").strip()
            if not oid or oid == "-":
                continue
            wi = int(row.get("Walk-in Customer") or 0) + int(row.get("Walk-in Non-Commercial") or 0) \
               + int(row.get("Walk-in Commercial") or 0) + int(row.get("Walk-in E-commerce") or 0)
            bb = int(row.get("Registered Bulk") or 0) + int(row.get("Bulk Non-Commercial") or 0) \
               + int(row.get("Bulk Commercial") or 0) + int(row.get("Bulk E-commerce") or 0)
            ps = int(row.get("On Postal Service") or 0) + int(row.get("Govt Service") or 0) \
               + int(row.get("Inter FPO") or 0)
            cm = int(row.get("Commercial") or 0) + int(row.get("E-commerce") or 0)
            other = (int(row.get("Non-Commercial") or 0) + int(row.get("Others") or 0)
                   + int(row.get("PIDPI") or 0) + int(row.get("Student Mail") or 0)
                   + int(row.get("BO Rebooking") or 0) + int(row.get("Free Active Service") or 0))
            r = out[oid]
            r["walk_in"] += wi; r["bulk_bnpl"] += bb; r["postal_service"] += ps
            r["commercial"] += cm; r["other"] += other
    return out


def build_scope(label, scope_offices, by_off, mix_by_off, hierarchy, total_offices_in_hier):
    """Aggregate a set of offices into the booking slice shape the renderer expects."""
    arts = 0; biz = 0.0
    prod_agg = defaultdict(lambda: {"articles": 0, "business": 0.0, "offices": set()})
    daily_agg = defaultdict(lambda: {"articles": 0, "business": 0.0})
    mix = {"walk_in": 0, "bulk_bnpl": 0, "postal_service": 0, "commercial": 0, "other": 0}
    active = 0

    office_summaries = []  # for top_offices
    for oid in scope_offices:
        rec = by_off.get(oid)
        if not rec:
            continue
        active += 1
        arts += rec["articles"]
        biz  += rec["business"]
        for pname, pv in rec["by_prod"].items():
            prod_agg[pname]["articles"] += pv["articles"]
            prod_agg[pname]["business"] += pv["business"]
            prod_agg[pname]["offices"].add(oid)
        for d, dv in rec["daily"].items():
            daily_agg[d]["articles"] += dv["articles"]
            daily_agg[d]["business"] += dv["business"]
        m = mix_by_off.get(oid, {})
        for k in mix: mix[k] += m.get(k, 0)
        office_summaries.append({
            "id":   oid,
            "name": rec["name"],
            "articles": rec["articles"],
            "business": rec["business"],
            "products": len(rec["products"]),
        })

    # Build product list sorted by business desc
    prod_list = []
    for pname, v in sorted(prod_agg.items(), key=lambda kv: -kv[1]["business"]):
        prod_list.append({
            "name":        pname,
            "articles":    v["articles"],
            "business":    round(v["business"], 2),
            "offices":     len(v["offices"]),
            "business_cr": round(v["business"] / CR, 4),
            "business_l":  round(v["business"] / L,  4),
        })

    # Daily list sorted by date
    daily_list = [{
        "date": d,
        "articles": daily_agg[d]["articles"],
        "business_l": round(daily_agg[d]["business"] / L, 4),
    } for d in sorted(daily_agg.keys())]

    # Peak / trough
    peak = max(daily_list, key=lambda x: x["articles"]) if daily_list else None
    trough = min(daily_list, key=lambda x: x["articles"]) if daily_list else None

    # Top 25 offices by business
    office_summaries.sort(key=lambda o: -o["business"])
    top25 = []
    for o in office_summaries[:25]:
        top25.append({
            "id":          o["id"],
            "name":        o["name"],
            "articles":    o["articles"],
            "business":    round(o["business"], 2),
            "products":    o["products"],
            "business_l":  round(o["business"] / L,  4),
            "avg_rs":      round(o["business"] / o["articles"], 2) if o["articles"] > 0 else 0,
        })

    days = len(daily_list)
    total_in_hier = total_offices_in_hier
    inactive = max(0, total_in_hier - active)

    mix["total"] = arts

    return {
        "label": label,
        "totals": {
            "articles":             arts,
            "business_cr":          round(biz / CR, 4),
            "business_l":           round(biz / L,  4),
            "active_offices":       active,
            "total_offices_in_hier": total_in_hier,
            "inactive_offices":     inactive,
            "products":             len(prod_list),
            "days":                 days,
            "avg_articles_per_day": round(arts / days, 4) if days > 0 else 0,
            "avg_rs_per_article":   round(biz  / arts, 4) if arts > 0 else 0,
        },
        "customer_mix": mix,
        "products":     prod_list,
        "daily":        daily_list,
        "top_offices":  top25,
        "peak_day":     {"date": peak["date"], "articles": peak["articles"], "business_l": peak["business_l"]} if peak else None,
        "trough_day":   {"date": trough["date"], "articles": trough["articles"], "business_l": trough["business_l"]} if trough else None,
    }


def merge_offices(rec_a, rec_b):
    """Merge two by_office records (used to build Cumulative)."""
    out = {
        "name": rec_a.get("name") or rec_b.get("name"),
        "articles": rec_a["articles"] + rec_b["articles"],
        "business": rec_a["business"] + rec_b["business"],
        "products": rec_a["products"] | rec_b["products"],
        "daily": defaultdict(lambda: {"articles": 0, "business": 0.0}),
        "by_prod": defaultdict(lambda: {"articles": 0, "business": 0.0}),
    }
    for d, v in rec_a["daily"].items():
        out["daily"][d]["articles"] += v["articles"]; out["daily"][d]["business"] += v["business"]
    for d, v in rec_b["daily"].items():
        out["daily"][d]["articles"] += v["articles"]; out["daily"][d]["business"] += v["business"]
    for p, v in rec_a["by_prod"].items():
        out["by_prod"][p]["articles"] += v["articles"]; out["by_prod"][p]["business"] += v["business"]
    for p, v in rec_b["by_prod"].items():
        out["by_prod"][p]["articles"] += v["articles"]; out["by_prod"][p]["business"] += v["business"]
    return out


def build_month(label, by_off, mix_by_off, hierarchy):
    """Build {label, by_div, by_region, circle} for one month."""
    # Group offices by div / region
    div_offices  = defaultdict(set)
    reg_offices  = defaultdict(set)
    all_offices  = set(by_off.keys())
    for oid in by_off.keys():
        info = hierarchy.get(oid)
        if not info: continue
        div_offices[info["division"]].add(oid)
        reg_offices[info["region"]].add(oid)

    # Compute total_offices_in_hier per scope from hierarchy
    div_hier_count = defaultdict(int)
    reg_hier_count = defaultdict(int)
    for oid, info in hierarchy.items():
        div_hier_count[info["division"]] += 1
        reg_hier_count[info["region"]]   += 1

    by_div_out = {}
    for div, offs in div_offices.items():
        if not div: continue
        by_div_out[div] = build_scope(div, offs, by_off, mix_by_off, hierarchy, div_hier_count[div])

    by_reg_out = {}
    for reg, offs in reg_offices.items():
        if not reg: continue
        by_reg_out[reg] = build_scope(reg, offs, by_off, mix_by_off, hierarchy, reg_hier_count[reg])

    circle = build_scope("AP Circle", all_offices, by_off, mix_by_off, hierarchy, len(hierarchy))

    return {"label": label, "circle": circle, "by_region": by_reg_out, "by_div": by_div_out}


# ── HTML/JS injection ────────────────────────────────────────────────────────
MARK = {
    "data_b": "// === BOOKING_BY_MONTH (auto-generated) ===",
    "data_e": "// === END BOOKING_BY_MONTH ===",
    "css_b":  "/* === BOOKING MONTH-SWITCHER STYLES === */",
    "css_e":  "/* === END BOOKING MONTH-SWITCHER STYLES === */",
    "html_b": "<!-- === BOOKING MONTH SWITCHER === -->",
    "html_e": "<!-- === END BOOKING MONTH SWITCHER === -->",
    "js_b":   "// === BOOKING MONTH SWITCHER LOGIC ===",
    "js_e":   "// === END BOOKING MONTH SWITCHER ===",
}

NEW_CSS = """
/* === BOOKING MONTH-SWITCHER STYLES === */
.bk-month-tabs {
  display: inline-flex; gap: 0;
  margin: 4px 0 14px;
  border: 1px solid var(--rule);
  background: var(--paper-warm);
}
.bk-month-tab {
  font-family: var(--font-mono); font-size: 12px;
  padding: 7px 16px; cursor: pointer;
  letter-spacing: 0.10em; text-transform: uppercase;
  color: var(--ink-soft);
  border: 0; background: transparent;
  border-right: 1px solid var(--rule);
}
.bk-month-tab:last-child { border-right: 0; }
.bk-month-tab.active {
  background: var(--ink-strong); color: var(--paper);
}
.bk-month-tab:hover:not(.active) {
  background: var(--paper); color: var(--ink);
}
.bk-month-label {
  font-family: var(--font-mono); font-size: 11px;
  letter-spacing: 0.12em; text-transform: uppercase;
  color: var(--ink-soft); margin-right: 12px;
}
/* === END BOOKING MONTH-SWITCHER STYLES === */
"""

NEW_HTML = """
<!-- === BOOKING MONTH SWITCHER === -->
<div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
  <span class="bk-month-label">View month:</span>
  <div class="bk-month-tabs" id="bk-month-tabs">
    <button class="bk-month-tab" data-bm="Apr-26" onclick="setBookingMonth('Apr-26')">April 2026</button>
    <button class="bk-month-tab" data-bm="May-26" onclick="setBookingMonth('May-26')">May 2026</button>
    <button class="bk-month-tab active" data-bm="Cumulative" onclick="setBookingMonth('Cumulative')">Apr–May 2026</button>
  </div>
</div>
<!-- === END BOOKING MONTH SWITCHER === -->
"""

NEW_JS = r"""
// === BOOKING MONTH SWITCHER LOGIC ===
var CUR_BOOKING_MONTH = 'Cumulative';
function setBookingMonth(m) {
  CUR_BOOKING_MONTH = m;
  document.querySelectorAll('.bk-month-tab').forEach(function(b){
    b.classList.toggle('active', b.dataset.bm === m);
  });
  if (typeof renderDivision === 'function' && typeof CUR_DIV_NAME !== 'undefined') {
    renderDivision(CUR_DIV_NAME);
  }
}
function pickBookingSliceMonthly(d, divName) {
  var pack = (typeof BOOKING_BY_MONTH !== 'undefined') ? BOOKING_BY_MONTH[CUR_BOOKING_MONTH] : null;
  if (!pack) return null;
  if (divName === '__CIRCLE__') return { B: pack.circle, scopeLabel: 'AP CIRCLE', isCircle: true };
  if (typeof divName === 'string' && divName.indexOf('__REGION__') === 0) {
    var reg = divName.replace('__REGION__','');
    var s = pack.by_region[reg];
    return { B: s || null, scopeLabel: reg.toUpperCase() + ' REGION', isCircle: false };
  }
  var s2 = pack.by_div[divName];
  return { B: s2 || null, scopeLabel: (divName || '').toUpperCase() + ' DIVISION', isCircle: false };
}
// === END BOOKING MONTH SWITCHER ===
"""


def patch_html(booking_by_month):
    html = HTML.read_text(encoding="utf-8")
    print("  Read index.html ({:,} chars)".format(len(html)))

    # 1) DATA constant — inject before the BOOKING_DATA constant
    data_block = (
        f"\n{MARK['data_b']}\n"
        f"const BOOKING_BY_MONTH = {json.dumps(booking_by_month, ensure_ascii=False, separators=(',',':'))};\n"
        f"{MARK['data_e']}\n"
    )
    if MARK["data_b"] in html:
        pat = re.compile(re.escape(MARK["data_b"]) + r".*?" + re.escape(MARK["data_e"]) + r"\n", re.DOTALL)
        html = pat.sub(lambda _m: data_block.lstrip("\n"), html, count=1)
        print("  Replaced BOOKING_BY_MONTH data")
    else:
        i = html.find("const BOOKING_DATA")
        if i < 0:
            print("  ERROR: no anchor 'const BOOKING_DATA'"); return False
        html = html[:i] + data_block.lstrip("\n") + "\n" + html[i:]
        print("  Inserted BOOKING_BY_MONTH data")

    # 2) CSS
    if MARK["css_b"] in html:
        pat = re.compile(re.escape(MARK["css_b"]) + r".*?" + re.escape(MARK["css_e"]), re.DOTALL)
        html = pat.sub(lambda _m: NEW_CSS.strip(), html, count=1)
        print("  Replaced month-switcher CSS")
    else:
        i = html.rfind("</style>")
        html = html[:i] + NEW_CSS + "\n" + html[i:]
        print("  Inserted month-switcher CSS")

    # 3) JS — inject before "function pickBookingSlice("
    if MARK["js_b"] in html:
        pat = re.compile(re.escape(MARK["js_b"]) + r".*?" + re.escape(MARK["js_e"]) + r"\n", re.DOTALL)
        html = pat.sub(lambda _m: NEW_JS.strip("\n") + "\n", html, count=1)
        print("  Replaced month-switcher JS")
    else:
        m = re.search(r"\nfunction pickBookingSlice\(", html)
        if not m:
            print("  ERROR: pickBookingSlice not found"); return False
        html = html[:m.start()] + "\n" + NEW_JS + "\n" + html[m.start():]
        print("  Inserted month-switcher JS")

    # 4) Wrap original pickBookingSlice — call the monthly version first
    hook = "  var _mo = pickBookingSliceMonthly(d, divName);\n  if (_mo && _mo.B) return _mo;\n"
    if hook not in html:
        m = re.search(r"function pickBookingSlice\([^)]*\)\s*\{\n", html)
        if m:
            html = html[:m.end()] + hook + html[m.end():]
            print("  Hooked pickBookingSlice to monthly source")

    # 5) Tab HTML — insert switcher just after <div id="tab-booking" class="tab-content">'s opening section-head
    if MARK["html_b"] in html:
        pat = re.compile(re.escape(MARK["html_b"]) + r".*?" + re.escape(MARK["html_e"]), re.DOTALL)
        html = pat.sub(lambda _m: NEW_HTML.strip(), html, count=1)
        print("  Replaced month-switcher HTML")
    else:
        # Find tab-booking open, then find first </div> after first <span class="desc"...></span>
        i = html.find('<div id="tab-booking"')
        if i < 0: print("  ERROR: tab-booking not found"); return False
        # Insert just before the first <div id="bk-daterange" ...>
        anchor = '<div id="bk-daterange"'
        j = html.find(anchor, i)
        if j < 0:
            print("  WARNING: bk-daterange not found, inserting at top of tab-booking")
            # Insert right after the section-head closing
            j = html.find("</div>", i) + len("</div>") + 1
        html = html[:j] + NEW_HTML.strip() + "\n  " + html[j:]
        print("  Inserted month-switcher HTML")

    HTML.write_text(html, encoding="utf-8")
    print("  Wrote index.html ({:,} chars)".format(len(html)))
    return True


if __name__ == "__main__":
    print("=== patch_booking_months.py ===")
    hier = load_hierarchy()
    print(f"  Hierarchy: {len(hier):,} offices")

    print("\nReading April CSVs...")
    apr_off, _apr_p, _apr_d = read_productwise(APR_PROD)
    apr_mix = read_booktypewise(APR_BOOK)
    print(f"  Apr: {len(apr_off):,} active offices, {sum(rec['articles'] for rec in apr_off.values()):,} articles")

    print("Reading May CSVs...")
    may_off, _may_p, _may_d = read_productwise(MAY_PROD)
    may_mix = read_booktypewise(MAY_BOOK)
    print(f"  May: {len(may_off):,} active offices, {sum(rec['articles'] for rec in may_off.values()):,} articles")

    print("Building Cumulative...")
    cum_off = {}
    all_oids = set(apr_off.keys()) | set(may_off.keys())
    EMPTY = {"name": None, "articles": 0, "business": 0.0,
             "products": set(),
             "daily": defaultdict(lambda: {"articles": 0, "business": 0.0}),
             "by_prod": defaultdict(lambda: {"articles": 0, "business": 0.0})}
    for oid in all_oids:
        a = apr_off.get(oid) or {**EMPTY, "products": set(), "daily": defaultdict(lambda: {"articles":0,"business":0.0}), "by_prod": defaultdict(lambda: {"articles":0,"business":0.0})}
        b = may_off.get(oid) or {**EMPTY, "products": set(), "daily": defaultdict(lambda: {"articles":0,"business":0.0}), "by_prod": defaultdict(lambda: {"articles":0,"business":0.0})}
        cum_off[oid] = merge_offices(a, b)
    cum_mix = defaultdict(lambda: {"walk_in": 0, "bulk_bnpl": 0, "postal_service": 0, "commercial": 0, "other": 0})
    for oid in set(apr_mix.keys()) | set(may_mix.keys()):
        for k in ["walk_in","bulk_bnpl","postal_service","commercial","other"]:
            cum_mix[oid][k] = apr_mix.get(oid,{}).get(k,0) + may_mix.get(oid,{}).get(k,0)

    print("Building monthly scopes...")
    apr_pack = build_month("Apr 2026",      apr_off, apr_mix, hier)
    may_pack = build_month("May 2026",      may_off, may_mix, hier)
    cum_pack = build_month("Apr-May 2026",  cum_off, cum_mix, hier)
    BBM = {"Apr-26": apr_pack, "May-26": may_pack, "Cumulative": cum_pack}

    # Sanity print
    for k, pack in BBM.items():
        c = pack["circle"]
        print(f"  {k}: circle {c['totals']['articles']:,} articles, {c['totals']['days']} days, peak {c['peak_day']['date'] if c['peak_day'] else '-'}")

    print("\nPatching index.html...")
    if patch_html(BBM):
        print("\n=== Done ===")
