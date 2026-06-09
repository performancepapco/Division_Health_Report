"""
build_from_excel.py
───────────────────────────────────────────────────────────────────────────────
Builds and injects monthly DATA into the Division Health Dashboard from Excel.

Usage:
    python build_from_excel.py <ecr_excel> <month_label> [booking_csv]

Examples:
    python build_from_excel.py "uploads/Division wise ECR May-2026.xlsx" "May-26"
    python build_from_excel.py "uploads/Division wise ECR May-2026.xlsx" "May-26" "uploads/booking_productwise_may.csv"

Month labels: Apr-26, May-26, Jun-26, Jul-26, Aug-26, Sep-26,
              Oct-26, Nov-26, Dec-26, Jan-27, Feb-27, Mar-27

ECR Excel column positions (0-indexed):
  0:  Division name
  1:  Region
  2:  Live Accounts
  6:  Silent Accounts
  13: GT of FS — total POSB revenue (Rs)          → actuals.POSB
  14: 801401 PLI PREMIUM (Rs)                      → pli.tbp_ach
  19: 801402 RPLI PREMIUM (Rs)                     → rpli.tbp_ach
  24: Total PLI/RPLI Rev. (Rs)                     → actuals.PLI/RPLI
  25: Parcel (Rs)                                  → actuals.Parcel
  26: MO (Rs)                                      → actuals.Mail Operations
  27: IRGB (Rs)                                    → actuals.IR & GB
  28: CCS (Rs)                                     → actuals.CCS
  31: Total revenue (Rs)                           → actuals.Total
  32: 3201 e-Lekha (total expenditure Rs)          → part of swap
  33: 3201 Plan (plan expenditure Rs)              → swap.Plan
  34: Exp. For ECR calculation (Rs)                → total_exp
  36: 320107 (pension Rs)                          → swap.Pension
"""

import sys, json, re, csv
from pathlib import Path
from collections import defaultdict

try:
    import openpyxl
except ImportError:
    print("ERROR: openpyxl not installed. Run: pip install openpyxl")
    sys.exit(1)

BASE = Path(__file__).parent
HTML = BASE / "index.html"
HIER_JSON = BASE / "office_hierarchy.json"
BOOKING_AGG_JSON = BASE / "_booking_aggregates.json"

MONTH_NAMES = {
    "Apr-26": "April-2026",  "May-26": "May-2026",   "Jun-26": "June-2026",
    "Jul-26": "July-2026",   "Aug-26": "August-2026", "Sep-26": "September-2026",
    "Oct-26": "October-2026","Nov-26": "November-2026","Dec-26": "December-2026",
    "Jan-27": "January-2027","Feb-27": "February-2027","Mar-27": "March-2027",
}
MONTH_ORDER = list(MONTH_NAMES.keys())

OFFICE_REGION_MAP = {
    "AP GM (Finance)":       "Circle",
    "Andhra Pradesh Circle": "Circle",
    "APCO":                  "Circle",
    "Kurnool Region":        "Kurnool",
    "PSD Vijayawada":        "Vijayawada",
    "Vijayawada Region":     "Vijayawada",
    "Visakhapatnam Region":  "Visakhapatnam",
}

CR = 10_000_000  # 1 Crore = 10 million Rupees

# ── Argument handling ─────────────────────────────────────────────────────────
if len(sys.argv) < 3:
    print(__doc__)
    sys.exit(1)

ecr_path    = Path(sys.argv[1])
month_key   = sys.argv[2]
booking_csv = Path(sys.argv[3]) if len(sys.argv) > 3 else None

if not ecr_path.exists():
    ecr_path = BASE / sys.argv[1]
if not ecr_path.exists():
    print(f"ERROR: ECR Excel not found: {sys.argv[1]}")
    sys.exit(1)

if month_key not in MONTH_NAMES:
    print(f"ERROR: Unknown month label '{month_key}'. Valid: {', '.join(MONTH_ORDER)}")
    sys.exit(1)

month_idx     = MONTH_ORDER.index(month_key)
num_months_fy = month_idx + 1  # months elapsed in FY (Apr=1, May=2, ...)
month_display = MONTH_NAMES[month_key]

print(f"Building {month_key} ({month_display}) — FY month {num_months_fy}")
print(f"ECR file: {ecr_path.name}")

# ── Load existing April DATA from index.html (for targets and PLI/RPLI meta) ──
with open(HTML, encoding="utf-8") as f:
    dash_src = f.read()

m = re.search(r'const DATA_BY_MONTH = \{ "Apr-26": (\{.+?\}) \};', dash_src)
if not m:
    print("ERROR: Could not find DATA_BY_MONTH['Apr-26'] in index.html.")
    sys.exit(1)

apr_data = json.loads(m.group(1))
print(f"  Loaded April DATA: {len(apr_data)} entries")

# ── Read ECR Excel ─────────────────────────────────────────────────────────────
print(f"Reading ECR Excel...")
wb = openpyxl.load_workbook(ecr_path, read_only=True, data_only=True)
ws = wb.active

def safe_num(v):
    if v is None: return 0.0
    try: return float(v)
    except: return 0.0

rows_by_div = {}
for i, row in enumerate(ws.iter_rows(values_only=True)):
    if i == 0: continue  # skip header
    name = str(row[0]).strip() if row[0] else ""
    if not name or name.lower() in ("totals", "total", "grand total"):
        continue
    rows_by_div[name] = row

wb.close()
print(f"  {len(rows_by_div)} rows read")

# ── Build per-division DATA ────────────────────────────────────────────────────
def build_division(name, row, apr_entry, is_office=False):
    """Build a division data entry from ECR row + April metadata."""
    apr = apr_entry or {}

    posb_rev    = safe_num(row[13]) / CR   # GT of FS
    pli_rpli    = safe_num(row[24]) / CR   # Total PLI/RPLI Rev
    parcel      = safe_num(row[25]) / CR
    mo          = safe_num(row[26]) / CR
    irgb        = safe_num(row[27]) / CR
    ccs         = safe_num(row[28]) / CR
    total_rev   = safe_num(row[31]) / CR   # Total revenue

    total_exp   = safe_num(row[34]) / CR   # Exp. for ECR calc
    pension     = safe_num(row[36]) / CR   # 320107
    plan        = safe_num(row[33]) / CR   # 3201 Plan

    pli_tbp     = safe_num(row[14]) / CR   # PLI Premium
    rpli_tbp    = safe_num(row[19]) / CR   # RPLI Premium

    live_accts  = int(safe_num(row[2]))
    silent_accts= int(safe_num(row[6]))

    actuals = {
        "Parcel":            parcel,
        "Mail Operations":   mo,
        "IR & GB":           irgb,
        "CCS":               ccs,
        "POSB":              posb_rev,
        "PLI/RPLI":          pli_rpli,
        "Total":             total_rev,
    }

    # Annual targets: same as April (FY27 targets don't change mid-year)
    targets = apr.get("targets", {k: 0 for k in actuals})

    # Pro-rata: targets * months_elapsed / 12 (cumulative FY pace)
    pro_rata = {k: (targets.get(k, 0) * num_months_fy / 12) for k in targets}

    # Attainments
    attainments = {}
    for v in ["Parcel", "Mail Operations", "IR & GB", "CCS", "POSB", "PLI/RPLI"]:
        pr = pro_rata.get(v, 0)
        attainments[v] = round((actuals.get(v, 0) / pr * 100), 1) if pr > 0 else 0.0

    composite_score = (actuals["Total"] / pro_rata.get("Total", 1) * 100) if pro_rata.get("Total", 0) > 0 else 0.0
    ecr_with_pension    = (actuals["Total"] / total_exp * 100) if total_exp > 0 else 0.0
    ecr_without_pension = (actuals["Total"] / (total_exp - pension) * 100) if (total_exp - pension) > 0 else 0.0

    # Swap: pension and plan are exact; distribute remainder proportionally from April
    apr_swap = apr.get("swap", {})
    apr_total = apr_swap.get("Total", 0) or 0
    apr_pension = apr_swap.get("Pension", 0) or 0
    apr_plan = apr_swap.get("Plan", 0) or 0
    apr_rest = apr_total - apr_pension - apr_plan

    may_rest = total_exp - pension - plan
    scale = (may_rest / apr_rest) if apr_rest > 0 else 1.0

    swap = {
        "Salaries":   round((apr_swap.get("Salaries", 0) or 0) * scale, 7),
        "Wages":      round((apr_swap.get("Wages", 0) or 0) * scale, 7),
        "Pension":    round(pension, 7),
        "Allowances": round((apr_swap.get("Allowances", 0) or 0) * scale, 7),
        "Plan":       round(plan, 7),
        "Other":      round((apr_swap.get("Other", 0) or 0) * scale, 7),
        "Total":      round(total_exp, 7),
    }
    # Adjust rounding: make sure swap sums to total_exp
    swap_sum = sum(v for k, v in swap.items() if k != "Total")
    diff = total_exp - swap_sum
    if abs(diff) > 0.0000001:
        swap["Other"] = round(swap["Other"] + diff, 7)

    # PLI/RPLI
    apr_pli  = apr.get("pli") or {}
    apr_rpli = apr.get("rpli") or {}
    apr_pli_nbp  = apr_pli.get("nbp_ach", 0) or 0
    apr_rpli_nbp = apr_rpli.get("nbp_ach", 0) or 0
    apr_pli_tbp  = (apr_pli.get("tbp_ach", 0) or 0)
    apr_rpli_tbp = (apr_rpli.get("tbp_ach", 0) or 0)

    # NBP: scale proportionally from April (no direct data in ECR Excel)
    nbp_pli_scale  = (apr_pli_nbp / apr_pli_tbp)   if apr_pli_tbp  > 0 else 0
    nbp_rpli_scale = (apr_rpli_nbp / apr_rpli_tbp)  if apr_rpli_tbp > 0 else 0

    pli = {
        "tbp_target": apr_pli.get("tbp_target", 0),
        "tbp_pro":    (apr_pli.get("tbp_target", 0) or 0) * num_months_fy / 12,
        "tbp_ach":    pli_tbp,
        "nbp_target": apr_pli.get("nbp_target", 0),
        "nbp_ach":    round(pli_tbp * nbp_pli_scale, 7),
        "sales_force":apr_pli.get("sales_force", 0),
        "yoy_growth": apr_pli.get("yoy_growth", 0),
    } if (apr_pli or pli_tbp > 0) else None

    rpli = {
        "tbp_target": apr_rpli.get("tbp_target", 0),
        "tbp_pro":    (apr_rpli.get("tbp_target", 0) or 0) * num_months_fy / 12,
        "tbp_ach":    rpli_tbp,
        "nbp_target": apr_rpli.get("nbp_target", 0),
        "nbp_ach":    round(rpli_tbp * nbp_rpli_scale, 7),
        "sales_force":apr_rpli.get("sales_force", 0),
        "yoy_growth": apr_rpli.get("yoy_growth", 0),
    } if (apr_rpli or rpli_tbp > 0) else None

    # POSB: update live/silent accounts; keep FY targets from April
    apr_posb_tgt = apr.get("posb_tgt") or {}
    posb_tgt = {
        "live_accounts":       live_accts,
        "silent_accounts":     silent_accts,
        "net_add_target_FY27": apr_posb_tgt.get("net_add_target_FY27", 0),
        "live_revenue":        apr_posb_tgt.get("live_revenue", 0),
        "silent_revenue":      apr_posb_tgt.get("silent_revenue", 0),
        "net_add_revenue":     apr_posb_tgt.get("net_add_revenue", 0),
    }

    # posb_hist: keep from April (FY26 historical data unchanged)
    posb_hist = apr.get("posb_hist")

    # Booking: will be updated separately from booking CSV; keep April as default
    booking = apr.get("booking") or {
        "total_business_cr": 0, "total_articles": 0,
        "active_offices": 0, "total_offices_in_hier": 0, "inactive_offices": 0,
        "wi_share": 0, "bnpl_share": 0, "wi_arts": 0, "bnpl_arts": 0,
        "products": [], "top_offices": [],
    }

    entry = {
        "region":              apr.get("region", ""),
        "targets":             targets,
        "actuals":             actuals,
        "pro_rata":            pro_rata,
        "attainments":         attainments,
        "composite_score":     round(composite_score, 10),
        "total_exp":           round(total_exp, 7),
        "ecr_with_pension":    round(ecr_with_pension, 10),
        "ecr_without_pension": round(ecr_without_pension, 10),
        "swap":                swap,
        "booking":             booking,
        "pli":                 pli,
        "rpli":                rpli,
        "posb_hist":           posb_hist,
        "posb_tgt":            posb_tgt,
        "mmu":                 apr.get("mmu", {"ebo": None, "obo": None}),
        "rank":                apr.get("rank", 0),
        "rank_in_region":      apr.get("rank_in_region", 0),
        "region_size":         apr.get("region_size", 0),
    }

    if is_office:
        entry["isOffice"] = True
        entry["targets"]    = {k: 0 for k in actuals}
        entry["pro_rata"]   = {k: 0 for k in actuals}
        entry["attainments"]= {k: 0 for k in ["Parcel","Mail Operations","IR & GB","CCS","POSB","PLI/RPLI"]}
        entry["composite_score"] = 0
        entry["ecr_with_pension"] = 0
        entry["ecr_without_pension"] = 0
        entry["swap"]["Salaries"] = 0
        entry["swap"]["Wages"] = 0
        entry["swap"]["Allowances"] = 0
        entry["swap"]["Other"] = 0

    return entry

# ── Identify which rows are regular divisions vs office entries ───────────────
known_divs = set(k for k, v in apr_data.items() if not v.get("isOffice"))
known_offices = set(k for k, v in apr_data.items() if v.get("isOffice"))

new_data = {}

# Process regular divisions
processed_divs = 0
for name, row in rows_by_div.items():
    if name in known_divs:
        apr_entry = apr_data.get(name, {})
        new_data[name] = build_division(name, row, apr_entry, is_office=False)
        processed_divs += 1

print(f"  Built {processed_divs} regular divisions")

# Process office entries (residual head offices)
processed_offices = 0
for name, row in rows_by_div.items():
    if name in OFFICE_REGION_MAP or name in known_offices:
        region = OFFICE_REGION_MAP.get(name) or (apr_data.get(name, {}).get("region") or "Circle")
        apr_entry = apr_data.get(name, {})
        if not apr_entry:
            # Create a minimal entry for known office types
            apr_entry = {"region": region, "swap": {}}
        entry = build_division(name, row, apr_entry, is_office=True)
        entry["region"] = region
        new_data[name] = entry
        processed_offices += 1

print(f"  Built {processed_offices} office entries")

# ── Compute ranks ─────────────────────────────────────────────────────────────
div_entries = [(n, v) for n, v in new_data.items() if not v.get("isOffice")]
div_entries.sort(key=lambda x: x[1]["composite_score"], reverse=True)
for i, (name, _) in enumerate(div_entries):
    new_data[name]["rank"] = i + 1

for reg in ["Vijayawada", "Visakhapatnam", "Kurnool"]:
    reg_divs = [(n, v) for n, v in div_entries if v["region"] == reg]
    reg_divs.sort(key=lambda x: x[1]["composite_score"], reverse=True)
    for i, (name, v) in enumerate(reg_divs):
        new_data[name]["rank_in_region"] = i + 1
        new_data[name]["region_size"] = len(reg_divs)

print(f"  Ranks computed")

# ── Process booking CSV (optional) ────────────────────────────────────────────
if booking_csv and booking_csv.exists():
    print(f"Processing booking CSV: {booking_csv.name}")
    with open(HIER_JSON, encoding="utf-8") as f:
        hierarchy = json.load(f)

    def get_div(office_id):
        rec = hierarchy.get(str(office_id).strip())
        if not rec: return None
        div = rec.get("division", "").replace(" Division", "").replace(" division", "").strip()
        return div if div else None

    WALK_IN_TYPES  = {"Walk-in", "Walk in", "Walk_in", "walk_in", "Walkin"}
    BNPL_TYPES = {"BNPL", "bnpl", "Bulk BNPL", "bulk_bnpl", "BulkBNPL"}

    div_booking = defaultdict(lambda: {
        "articles": 0, "revenue": 0.0, "wi_arts": 0, "bnpl_arts": 0,
        "offices": set(), "prods": defaultdict(lambda: {"arts": 0, "rev": 0.0, "offices": set()}),
        "top_offices": defaultdict(lambda: {"arts": 0, "rev": 0.0, "name": ""}),
    })

    def clean_num(v):
        if v is None: return 0.0
        try: return float(str(v).replace(",","").strip())
        except: return 0.0

    with open(booking_csv, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            oid = str(row.get("office-id", "")).strip()
            if not oid: continue
            div = get_div(oid)
            if not div or div not in known_divs: continue

            arts = int(clean_num(row.get("article-count", 0)))
            rev  = clean_num(row.get("total_amount", 0))
            prod = str(row.get("product-name", "")).strip()
            oname = str(row.get("office-name", "")).strip()
            btype = str(row.get("booking-type", "")).strip()

            b = div_booking[div]
            b["articles"]  += arts
            b["revenue"]   += rev
            b["offices"].add(oid)
            b["prods"][prod]["arts"]      += arts
            b["prods"][prod]["rev"]       += rev
            b["prods"][prod]["offices"].add(oid)
            b["top_offices"][oid]["arts"] += arts
            b["top_offices"][oid]["rev"]  += rev
            b["top_offices"][oid]["name"]  = oname

            if btype in WALK_IN_TYPES:  b["wi_arts"]   += arts
            if btype in BNPL_TYPES:     b["bnpl_arts"]  += arts

    for div, b in div_booking.items():
        if div not in new_data: continue
        tot = b["articles"] or 1
        products = sorted(
            [{"name": p, "articles": v["arts"], "revenue_lakhs": round(v["rev"]/100000, 4),
              "offices": len(v["offices"])} for p, v in b["prods"].items()],
            key=lambda x: x["articles"], reverse=True
        )[:10]
        top_offices = sorted(
            [{"office_id": oid, "name": v["name"], "articles": v["arts"],
              "revenue": round(v["rev"], 2)} for oid, v in b["top_offices"].items()],
            key=lambda x: x["articles"], reverse=True
        )[:10]

        # Count active offices from hierarchy
        div_offices = [o for o, r in hierarchy.items() if
                       r.get("division", "").replace(" Division","").strip() == div]
        total_offices = len(div_offices)
        active_offices = len(b["offices"])
        inactive_offices = max(0, total_offices - active_offices)

        new_data[div]["booking"] = {
            "total_business_cr": round(b["revenue"] / CR, 6),
            "total_articles":    b["articles"],
            "active_offices":    active_offices,
            "total_offices_in_hier": total_offices,
            "inactive_offices":  inactive_offices,
            "wi_share":  round(b["wi_arts"]   / tot * 100, 2),
            "bnpl_share":round(b["bnpl_arts"]  / tot * 100, 2),
            "wi_arts":   b["wi_arts"],
            "bnpl_arts": b["bnpl_arts"],
            "products":  products,
            "top_offices": top_offices,
        }
    print(f"  Booking data updated for {len(div_booking)} divisions")
else:
    print("  No booking CSV provided — keeping April booking data")

# ── Inject into index.html ────────────────────────────────────────────────────
data_json = json.dumps(new_data, separators=(",", ":"), ensure_ascii=False)
injection_line = f'DATA_BY_MONTH["{month_key}"] = {data_json};\n'
marker = f'DATA_BY_MONTH["{month_key}"]'

if marker in dash_src:
    existing_pat = re.compile(re.escape(f'DATA_BY_MONTH["{month_key}"]') + r'\s*=\s*\{.+?\};\n', re.DOTALL)
    m2 = existing_pat.search(dash_src)
    if m2:
        dash_src = dash_src[:m2.start()] + injection_line + dash_src[m2.end():]
        print(f"  Replaced existing {month_key} data in index.html")
    else:
        print(f"WARNING: Marker found but regex replace failed. Appending.")
        dash_src += f'\n<script>{injection_line}</script>'
else:
    insert_match = re.search(r'(const DATA_BY_MONTH = \{ "Apr-26": \{.+?\} \};)\n', dash_src)
    if not insert_match:
        print("ERROR: Cannot locate DATA_BY_MONTH declaration for insertion.")
        sys.exit(1)
    dash_src = dash_src[:insert_match.end()] + injection_line + dash_src[insert_match.end():]
    print(f"  Inserted {month_key} data into index.html")

# ── Update month selector dropdowns ──────────────────────────────────────────
def update_select(html, sel_id, mk, md):
    pat = re.compile(r'(<select id="' + sel_id + r'"[^>]*>)(.*?)(</select>)', re.DOTALL)
    m = pat.search(html)
    if not m: return html, False
    options = re.sub(r' selected', '', m.group(2))
    options = re.sub(r'\s*<option value="' + re.escape(mk) + r'"[^>]*>[^<]*</option>', '', options)
    new_opt = f'<option value="{mk}" selected>{md}</option>'
    later_keys = MONTH_ORDER[MONTH_ORDER.index(mk)+1:]
    insert_before = None
    for lk in later_keys:
        lm = re.search(r'<option value="' + re.escape(lk) + r'"', options)
        if lm: insert_before = lm.start(); break
    if insert_before is not None:
        options = options[:insert_before] + '\n        ' + new_opt + options[insert_before:]
    else:
        options = options.rstrip() + '\n        ' + new_opt + '\n      '
    return html[:m.start()] + m.group(1) + options + m.group(3) + html[m.end():], True

dash_src, ok1 = update_select(dash_src, "month-from", month_key, month_display)
dash_src, ok2 = update_select(dash_src, "month-to",   month_key, month_display)
if ok1 and ok2:
    print(f"  Month selectors updated with {month_display}")

# ── Update CUR_MONTH_LABEL default ───────────────────────────────────────────
cur_label = re.search(r"let CUR_MONTH_LABEL = '([^']+)';", dash_src)
if cur_label:
    dash_src = dash_src.replace(f"let CUR_MONTH_LABEL = '{cur_label.group(1)}';",
                                f"let CUR_MONTH_LABEL = '{month_key}';")
    print(f"  Default month label set to {month_key}")

# ── Write file ────────────────────────────────────────────────────────────────
with open(HTML, "w", encoding="utf-8") as f:
    f.write(dash_src)

print(f"\nDone. Open index.html to view {month_display} data.")
print(f"  Select '{month_display}' to see cumulative Apr–{month_key[:3]} performance.")
print(f"  Select 'April-2026' to see April-only performance.")
print(f"  Use the range selector for multi-month views.")
