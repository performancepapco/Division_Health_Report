#!/usr/bin/env python3
"""
patch_may2026.py
────────────────
Patches index.html with:
  1. POSB account activity data  (Apr+May 2026 combined)
  2. PLI policies + premium data (April and May cumulative)
  3. RPLI policies + premium data (April and May cumulative)
  4. May 2026 booking data        (from CSV files)
  5. Separate POSB / PLI / RPLI tabs with rich visualisations

Run:  python patch_may2026.py
"""

import re, json, csv
from pathlib import Path
from collections import defaultdict

BASE = Path(__file__).parent
HTML = BASE / "index.html"
HIER = BASE / "office_hierarchy.json"
APR_BK = BASE / "_booking_aggregates.json"
MAY_PW_CSV = BASE / "uploads" / "may_2026" / "Booking_Productwise_Report (2).csv"
MAY_BK_CSV = BASE / "uploads" / "may_2026" / "Booking_BookTypewise_Datewise_Report (1).csv"

CR = 10_000_000  # 1 Crore

# ─── 1. HARDCODED PLI / RPLI / POSB DATA ──────────────────────────────────────

# format: (name, total_offices, offices_procured, policies, premium_rs, region)
PLI_APR_RAW = [
    ("Visakhapatnam", 157,  69,  311, 4376464, "Visakhapatnam"),
    ("Bhimavaram",    285,  62,  156, 2754358, "Vijayawada"),
    ("Srikakulam",    564,  85,  251, 2609095, "Visakhapatnam"),
    ("Narasaraopet",  446,  54,  119, 2310544, "Vijayawada"),
    ("Vijayawada",    360,  52,  128, 1674489, "Vijayawada"),
    ("Anakapalle",    606,  60,  106, 1668598, "Visakhapatnam"),
    ("Anantapur",     470,  50,  111, 1655717, "Kurnool"),
    ("Kakinada",      334,  43,  110, 1501505, "Visakhapatnam"),
    ("Cuddapah",      448,  47,  110, 1434497, "Kurnool"),
    ("Tirupati",      460,  60,  173, 1387312, "Kurnool"),
    ("Kurnool",       434,  50,   95, 1386643, "Kurnool"),
    ("Rajahmundry",   369,  35,   87, 1355957, "Visakhapatnam"),
    ("Proddatur",     375,  35,   79, 1273352, "Kurnool"),
    ("Prakasam",      449,  38,   73, 1123871, "Vijayawada"),
    ("Gudur",         336,  23,   41, 1105819, "Vijayawada"),
    ("Tadepalligudem",229,  28,   52, 1090598, "Vijayawada"),
    ("Chittoor",      424,  44,  110, 1046389, "Kurnool"),
    ("Nellore",       433,  35,   62,  981686, "Vijayawada"),
    ("Guntur",        175,  36,   64,  957717, "Vijayawada"),
    ("Eluru",         256,  31,   59,  878651, "Vijayawada"),
    ("Tenali",        268,  39,   76,  853453, "Vijayawada"),
    ("Nandyal",       330,  45,   78,  790741, "Kurnool"),
    ("Vizianagaram",  327,  33,   94,  675784, "Visakhapatnam"),
    ("Parvathipuram", 444,  48,  102,  670248, "Visakhapatnam"),
    ("Machilipatnam", 187,  26,   46,  627438, "Vijayawada"),
    ("Hindupur",      471,  29,   54,  547014, "Kurnool"),
    ("Markapur",      460,  23,   59,  531660, "Vijayawada"),
    ("Amalapuram",    234,  29,   59,  436812, "Visakhapatnam"),
    ("Gudivada",      247,  31,   61,  390459, "Vijayawada"),
]
PLI_APR_CIRCLE = (10578, 1240, 2926, 38096871)

# May cumulative (Apr + May)
PLI_MAY_RAW = [
    ("Visakhapatnam", 157,  88,  453, 7000868, "Visakhapatnam"),
    ("Vijayawada",    360,  93,  288, 6744278, "Vijayawada"),
    ("Anakapalle",    606, 167,  338, 5517275, "Visakhapatnam"),
    ("Nandyal",       330, 113,  314, 4349133, "Kurnool"),
    ("Hindupur",      471, 142,  296, 4217092, "Kurnool"),
    ("Machilipatnam", 187,  96,  209, 3808162, "Vijayawada"),
    ("Bhimavaram",    285,  73,  213, 3701835, "Vijayawada"),
    ("Tirupati",      460, 141,  306, 3458549, "Kurnool"),
    ("Cuddapah",      448, 134,  275, 3245284, "Kurnool"),
    ("Kurnool",       434, 125,  451, 3235915, "Kurnool"),
    ("Rajahmundry",   369,  79,  196, 2864606, "Visakhapatnam"),
    ("Guntur",        175,  55,  170, 2827289, "Vijayawada"),
    ("Vizianagaram",  327,  74,  201, 2785579, "Visakhapatnam"),
    ("Chittoor",      424, 110,  245, 2534584, "Kurnool"),
    ("Kakinada",      334,  67,  143, 2515019, "Visakhapatnam"),
    ("Tadepalligudem",229,  80,  168, 2400318, "Vijayawada"),
    ("Srikakulam",    564, 115,  267, 2310232, "Visakhapatnam"),
    ("Proddatur",     375, 113,  214, 2271172, "Kurnool"),
    ("Anantapur",     470,  99,  214, 2211316, "Kurnool"),
    ("Parvathipuram", 444,  98,  195, 2140417, "Visakhapatnam"),
    ("Tenali",        268,  77,  160, 1953598, "Vijayawada"),
    ("Eluru",         256,  46,  122, 1903868, "Vijayawada"),
    ("Prakasam",      449, 106,  203, 1854239, "Vijayawada"),
    ("Gudur",         336,  77,  150, 1708204, "Vijayawada"),
    ("Markapur",      460,  63,  120, 1605201, "Vijayawada"),
    ("Gudivada",      247,  51,  108, 1575755, "Vijayawada"),
    ("Amalapuram",    234,  69,  127, 1467547, "Visakhapatnam"),
    ("Narasaraopet",  446,  58,  100, 1465206, "Vijayawada"),
    ("Nellore",       433,  54,  124, 1360372, "Vijayawada"),
]
PLI_MAY_CIRCLE = (10578, 2663, 6370, 85032913)

RPLI_APR_RAW = [
    ("Srikakulam",    564, 215,  669, 2992438, "Visakhapatnam"),
    ("Narasaraopet",  446, 158,  394, 2929634, "Vijayawada"),
    ("Bhimavaram",    285, 131,  419, 2920179, "Vijayawada"),
    ("Kurnool",       434,  89,  202, 2104386, "Kurnool"),
    ("Parvathipuram", 444, 139,  368, 2058302, "Visakhapatnam"),
    ("Cuddapah",      448, 104,  269, 1986978, "Kurnool"),
    ("Tirupati",      460, 105,  307, 1941474, "Kurnool"),
    ("Vijayawada",    360, 121,  369, 1805160, "Vijayawada"),
    ("Anantapur",     470, 102,  233, 1545394, "Kurnool"),
    ("Anakapalle",    606, 122,  224, 1540397, "Visakhapatnam"),
    ("Nellore",       433,  77,  159, 1433770, "Vijayawada"),
    ("Nandyal",       330,  79,  171, 1391718, "Kurnool"),
    ("Kakinada",      334,  71,  222, 1346346, "Visakhapatnam"),
    ("Gudivada",      247,  95,  318, 1341903, "Vijayawada"),
    ("Eluru",         256,  66,  192, 1271762, "Vijayawada"),
    ("Chittoor",      424,  97,  263, 1218353, "Kurnool"),
    ("Rajahmundry",   369,  83,  200, 1166972, "Visakhapatnam"),
    ("Hindupur",      471, 106,  246, 1114948, "Kurnool"),
    ("Markapur",      460,  82,  169,  946461, "Vijayawada"),
    ("Proddatur",     375,  64,  121,  851133, "Kurnool"),
    ("Vizianagaram",  327,  83,  154,  802425, "Visakhapatnam"),
    ("Prakasam",      449,  81,  164,  756511, "Vijayawada"),
    ("Amalapuram",    234,  63,  151,  704109, "Visakhapatnam"),
    ("Tadepalligudem",229,  60,  122,  685713, "Vijayawada"),
    ("Gudur",         336,  52,  125,  635235, "Vijayawada"),
    ("Tenali",        268,  71,  142,  531078, "Vijayawada"),
    ("Machilipatnam", 187,  47,  101,  476953, "Vijayawada"),
    ("Guntur",        175,  46,   91,  430738, "Vijayawada"),
    ("Visakhapatnam", 157,  30,   49,  238109, "Visakhapatnam"),
]
RPLI_APR_CIRCLE = (10578, 2639, 6614, 39168579)

RPLI_MAY_RAW = [
    ("Anakapalle",    606, 367,  901, 7241952, "Visakhapatnam"),
    ("Parvathipuram", 444, 272,  925, 7041047, "Visakhapatnam"),
    ("Cuddapah",      448, 272,  700, 6240436, "Kurnool"),
    ("Hindupur",      471, 299,  968, 5834426, "Kurnool"),
    ("Srikakulam",    564, 385, 1102, 5691629, "Visakhapatnam"),
    ("Kurnool",       434, 225,  786, 5492594, "Kurnool"),
    ("Chittoor",      424, 232,  747, 4955700, "Kurnool"),
    ("Vijayawada",    360, 235,  721, 4661176, "Vijayawada"),
    ("Nandyal",       330, 200,  502, 4428865, "Kurnool"),
    ("Bhimavaram",    285, 198,  551, 4124676, "Vijayawada"),
    ("Tirupati",      460, 249,  713, 4055537, "Kurnool"),
    ("Machilipatnam", 187, 150,  525, 4043353, "Vijayawada"),
    ("Rajahmundry",   369, 195,  479, 4003423, "Visakhapatnam"),
    ("Anantapur",     470, 242,  611, 3955579, "Kurnool"),
    ("Narasaraopet",  446, 194,  472, 3899612, "Vijayawada"),
    ("Amalapuram",    234, 172,  499, 3786254, "Visakhapatnam"),
    ("Gudur",         336, 147,  369, 3783254, "Vijayawada"),
    ("Vizianagaram",  327, 204,  542, 3650864, "Visakhapatnam"),
    ("Markapur",      460, 204,  453, 3469597, "Vijayawada"),
    ("Prakasam",      449, 212,  475, 3091589, "Vijayawada"),
    ("Tadepalligudem",229, 175,  473, 3047630, "Vijayawada"),
    ("Kakinada",      334, 194,  421, 2999227, "Visakhapatnam"),
    ("Eluru",         256, 144,  470, 2979333, "Vijayawada"),
    ("Proddatur",     375, 184,  416, 2718425, "Kurnool"),
    ("Nellore",       433, 160,  379, 2679146, "Vijayawada"),
    ("Gudivada",      247, 172,  496, 2395341, "Vijayawada"),
    ("Tenali",        268, 146,  321, 1733957, "Vijayawada"),
    ("Guntur",        175,  88,  201, 1364401, "Vijayawada"),
    ("Visakhapatnam", 157,  47,  119,  533412, "Visakhapatnam"),
]
RPLI_MAY_CIRCLE = (10578, 5964, 16337, 113902435)

# POSB Actuals: (name, offices, opened, closed, net, region)
POSB_RAW = [
    ("Anakapalle",    606, 21769,  9251, 12518, "Visakhapatnam"),
    ("Cuddapah",      448, 24813, 16249,  8564, "Kurnool"),
    ("Machilipatnam", 190, 16072,  7653,  8419, "Vijayawada"),
    ("Proddatur",     376, 17740, 11245,  6495, "Kurnool"),
    ("Narasaraopet",  446, 17377, 11404,  5973, "Vijayawada"),
    ("Visakhapatnam", 158, 12598,  6856,  5742, "Visakhapatnam"),
    ("Tirupati",      461, 20582, 15582,  5000, "Kurnool"),
    ("Kurnool",       434, 15907, 11402,  4505, "Kurnool"),
    ("Kakinada",      334, 11911,  7608,  4303, "Visakhapatnam"),
    ("Gudivada",      247, 10608,  6704,  3904, "Vijayawada"),
    ("Tenali",        268, 11664,  7813,  3851, "Vijayawada"),
    ("Rajahmundry",   370, 10700,  6864,  3836, "Visakhapatnam"),
    ("Prakasam",      449, 16725, 13034,  3691, "Vijayawada"),
    ("Vijayawada",    363, 14441, 11258,  3183, "Vijayawada"),
    ("Srikakulam",    576, 15625, 12567,  3058, "Visakhapatnam"),
    ("Anantapur",     472, 14441, 11997,  2444, "Kurnool"),
    ("Nandyal",       331, 15399, 13136,  2263, "Kurnool"),
    ("Markapur",      462, 18856, 16671,  2185, "Vijayawada"),
    ("Hindupur",      472, 14124, 12080,  2044, "Kurnool"),
    ("Vizianagaram",  343,  8567,  6704,  1863, "Visakhapatnam"),
    ("Tadepalligudem",229, 10614,  8885,  1729, "Vijayawada"),
    ("Nellore",       436, 16080, 14371,  1709, "Vijayawada"),
    ("Amalapuram",    235,  9347,  7763,  1584, "Visakhapatnam"),
    ("Bhimavaram",    285, 14837, 13759,  1078, "Vijayawada"),
    ("Gudur",         336,  6452,  6041,   411, "Vijayawada"),
    ("Chittoor",      425, 24075, 23827,   248, "Kurnool"),
    ("Eluru",         256,  6759,  6937,  -178, "Vijayawada"),
    ("Guntur",        176, 10031, 10222,  -191, "Vijayawada"),
    ("Parvathipuram", 444,  8253,  8854,  -601, "Visakhapatnam"),
]
POSB_CIRCLE = (10628, 416367, 316737, 99630)
POSB_REGIONS = {
    "Kurnool":       (3419, 147081, 115518, 31563),
    "Vijayawada":    (4143, 170516, 134752, 35764),
    "Visakhapatnam": (3066,  98770,  66467, 32303),
}

# ─── 2. PROCESS MAY BOOKING DATA ──────────────────────────────────────────────

def load_hierarchy():
    with open(HIER) as f:
        return json.load(f)

def process_may_booking(hierarchy):
    """Read May productwise CSV, aggregate total_amount and article_count by division."""
    div_arts   = defaultdict(int)
    div_biz    = defaultdict(float)
    div_wi     = defaultdict(int)
    div_bnpl   = defaultdict(int)
    rms_names  = {"RMS AG", "RMS TP", "RMS V", "RMS Y"}

    if not MAY_PW_CSV.exists():
        print(f"  WARNING: May CSV not found: {MAY_PW_CSV}")
        return {}

    with open(MAY_PW_CSV, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            oid = str(row.get('office-id', '')).strip()
            if not oid or oid == '-':
                continue
            info = hierarchy.get(oid)
            if not info:
                continue
            div = info['division']
            arts  = int(row.get('article-count', 0) or 0)
            amt   = float(row.get('total_amount', 0) or 0)
            div_arts[div] += arts
            div_biz[div]  += amt

    # Also process booktype CSV for walk-in / BNPL split
    if MAY_BK_CSV.exists():
        with open(MAY_BK_CSV, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                oid = str(row.get('Office ID', '')).strip()
                if not oid or oid == '-':
                    continue
                info = hierarchy.get(oid)
                if not info:
                    continue
                div = info['division']
                wi   = int(row.get('Walk-in Customer', 0) or 0)
                bnpl = int(row.get('Registered Bulk', 0) or 0)
                div_wi[div]   += wi
                div_bnpl[div] += bnpl

    result = {}
    for div in set(list(div_arts.keys()) + list(div_biz.keys())):
        arts = div_arts[div]
        biz  = div_biz[div]
        wi   = div_wi.get(div, 0)
        bnpl = div_bnpl.get(div, 0)
        result[div] = {
            'articles': arts,
            'business_cr': round(biz / CR, 4),
            'wi_arts': wi,
            'bnpl_arts': bnpl,
            'wi_share': round(wi / arts * 100, 1) if arts > 0 else 0,
            'bnpl_share': round(bnpl / arts * 100, 1) if arts > 0 else 0,
        }
    return result

def build_may26_injection(apr_bk_json, may_bk_by_div):
    """
    Build DATA_BY_MONTH['May-26'] as a deep-copy of Apr-26 data,
    with booking totals updated to cumulative (Apr + May).
    Returns the JS injection string.
    """
    try:
        with open(apr_bk_json) as f:
            apr_bk = json.load(f)
    except Exception:
        apr_bk = {}

    # Get per-division April booking totals
    apr_div_arts = {}
    apr_div_biz  = {}
    apr_div_wi   = {}
    apr_div_bnpl = {}
    for div_name, info in apr_bk.items():
        if div_name in ("CIRCLE", "KURNOOL_REG", "VIJAYAWADA_REG", "VISAKHAPATNAM_REG"):
            continue
        t = info.get('totals', {})
        apr_div_arts[div_name] = t.get('articles', 0)
        apr_div_biz[div_name]  = t.get('business_cr', 0)
        apr_div_wi[div_name]   = info.get('customer_mix', {}).get('walk_in', 0)
        apr_div_bnpl[div_name] = info.get('customer_mix', {}).get('bulk_bnpl', 0)

    lines = ["DATA_BY_MONTH['May-26'] = JSON.parse(JSON.stringify(DATA_BY_MONTH['Apr-26']));"]
    lines.append("(function(){")
    lines.append("  var M = DATA_BY_MONTH['May-26'];")
    lines.append("  var mayBk = " + json.dumps(may_bk_by_div, ensure_ascii=False) + ";")
    lines.append("  var aprArts = " + json.dumps(apr_div_arts, ensure_ascii=False) + ";")
    lines.append("  var aprBiz  = " + json.dumps(apr_div_biz, ensure_ascii=False) + ";")
    lines.append("  var aprWi   = " + json.dumps(apr_div_wi, ensure_ascii=False) + ";")
    lines.append("  var aprBnpl = " + json.dumps(apr_div_bnpl, ensure_ascii=False) + ";")
    lines.append("""
  Object.keys(M).forEach(function(k) {
    var d = M[k];
    if (!d || !d.booking) return;
    var mb = mayBk[k] || {};
    var mayArts = mb.articles || 0;
    var mayBiz  = mb.business_cr || 0;
    var mayWi   = mb.wi_arts || 0;
    var mayBnpl = mb.bnpl_arts || 0;
    var cumArts = (aprArts[k] || 0) + mayArts;
    var cumBiz  = (aprBiz[k]  || 0) + mayBiz;
    var cumWi   = (aprWi[k]   || 0) + mayWi;
    var cumBnpl = (aprBnpl[k] || 0) + mayBnpl;
    d.booking.total_articles    = cumArts;
    d.booking.total_business_cr = cumBiz;
    d.booking.wi_arts           = cumWi;
    d.booking.bnpl_arts         = cumBnpl;
    d.booking.wi_share   = cumArts > 0 ? cumWi   / cumArts * 100 : 0;
    d.booking.bnpl_share = cumArts > 0 ? cumBnpl / cumArts * 100 : 0;
    if (mayArts > 0) d.booking.active_offices = d.booking.active_offices || 0;
  });
})();""")
    return "\n".join(lines)

# ─── 3. BUILD JS CONSTANTS ────────────────────────────────────────────────────

def raw_to_obj(raw, circle):
    obj = {}
    for (name, tot_off, off_proc, pols, prem, reg) in raw:
        obj[name] = {
            "total_offices": tot_off,
            "offices_procured": off_proc,
            "policies": pols,
            "premium": prem,
            "procurement_rate": round(off_proc / tot_off * 100, 1) if tot_off > 0 else 0,
            "avg_premium": round(prem / pols) if pols > 0 else 0,
            "region": reg,
        }
    obj["__CIRCLE__"] = {
        "total_offices": circle[0],
        "offices_procured": circle[1],
        "policies": circle[2],
        "premium": circle[3],
        "procurement_rate": round(circle[1] / circle[0] * 100, 1) if circle[0] > 0 else 0,
        "avg_premium": round(circle[3] / circle[2]) if circle[2] > 0 else 0,
    }
    return obj

def posb_to_obj(raw, circle, regions):
    obj = {}
    for (name, offices, opened, closed, net, region) in raw:
        obj[name] = {
            "offices": offices,
            "opened": opened,
            "closed": closed,
            "net": net,
            "region": region,
        }
    obj["__CIRCLE__"] = {
        "offices": circle[0],
        "opened": circle[1],
        "closed": circle[2],
        "net": circle[3],
    }
    for reg, (offices, opened, closed, net) in regions.items():
        obj[f"__REG_{reg}__"] = {
            "offices": offices,
            "opened": opened,
            "closed": closed,
            "net": net,
        }
    return obj

PLI_POLICIES = {
    "Apr-26": raw_to_obj(PLI_APR_RAW, PLI_APR_CIRCLE),
    "May-26": raw_to_obj(PLI_MAY_RAW, PLI_MAY_CIRCLE),
}
RPLI_POLICIES = {
    "Apr-26": raw_to_obj(RPLI_APR_RAW, RPLI_APR_CIRCLE),
    "May-26": raw_to_obj(RPLI_MAY_RAW, RPLI_MAY_CIRCLE),
}
POSB_ACTUALS = posb_to_obj(POSB_RAW, POSB_CIRCLE, POSB_REGIONS)

# ─── 4. GENERATE NEW CSS ──────────────────────────────────────────────────────

NEW_CSS = """
/* ============ POSB / PLI / RPLI TAB STYLES ============ */
.ins-kpi-strip {
  display: grid;
  gap: 1px;
  background: var(--rule);
  border: 1px solid var(--rule);
  margin-bottom: 18px;
}
.ins-kpi-strip.cols-4 { grid-template-columns: repeat(4,1fr); }
.ins-kpi-strip.cols-3 { grid-template-columns: repeat(3,1fr); }
.ins-kpi-strip.cols-2 { grid-template-columns: repeat(2,1fr); }

.ins-kpi {
  background: var(--paper);
  padding: 16px 20px 18px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.ins-kpi.feature { background: var(--ink-strong); color: var(--paper); }
.ins-kpi.green-bg { background: var(--green-pale); border-left: 3px solid var(--green); }
.ins-kpi.red-bg   { background: var(--red-pale);   border-left: 3px solid var(--red); }
.ins-kpi.amber-bg { background: var(--amber-pale);  border-left: 3px solid var(--amber); }
.ins-kpi-label {
  font-family: var(--font-mono);
  font-size: 14px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--ink-soft);
  font-weight: 500;
}
.ins-kpi.feature .ins-kpi-label { color: oklch(0.72 0.04 80); }
.ins-kpi-value {
  font-family: var(--font-serif);
  font-size: 32px;
  font-weight: 500;
  color: var(--ink-strong);
  line-height: 1;
  letter-spacing: -0.02em;
  font-variation-settings: "opsz" 48;
}
.ins-kpi.feature .ins-kpi-value { color: var(--paper); }
.ins-kpi-sub {
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--ink-faint);
  letter-spacing: 0.04em;
  margin-top: 2px;
}
.ins-kpi.feature .ins-kpi-sub { color: oklch(0.68 0.03 80); }

/* Division bars for POSB/PLI/RPLI */
.ins-div-bars { display: flex; flex-direction: column; gap: 3px; margin-bottom: 8px; }
.ins-bar-row {
  display: grid;
  grid-template-columns: 180px 1fr 90px 80px;
  align-items: center;
  gap: 10px;
  padding: 5px 0;
  border-bottom: 1px solid var(--rule);
}
.ins-bar-row:last-child { border-bottom: 0; }
.ins-bar-name {
  font-family: var(--font-sans);
  font-size: 14px;
  color: var(--ink);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.ins-bar-name .region-tag {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--ink-faint);
  margin-left: 5px;
  letter-spacing: 0.06em;
}
.ins-bar-track {
  height: 18px;
  background: var(--paper-warm);
  border-radius: 2px;
  overflow: hidden;
  position: relative;
}
.ins-bar-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.3s ease;
}
.ins-bar-fill.pos { background: var(--green); }
.ins-bar-fill.neg { background: var(--red); }
.ins-bar-fill.hi  { background: var(--accent); }
.ins-bar-fill.med { background: var(--amber); }
.ins-bar-fill.lo  { background: oklch(0.60 0.06 245); }
.ins-bar-val {
  font-family: var(--font-mono);
  font-size: 13.5px;
  color: var(--ink);
  text-align: right;
  font-weight: 600;
}
.ins-bar-val.pos { color: var(--green); }
.ins-bar-val.neg { color: var(--red); }
.ins-bar-sub {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--ink-faint);
  text-align: right;
}

/* Month comparison panel */
.month-compare {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 1px;
  background: var(--rule);
  border: 1px solid var(--rule);
  margin-bottom: 18px;
}
.month-col {
  background: var(--paper);
  padding: 14px 18px;
}
.month-col.header { background: var(--paper-deep); }
.month-col h4 {
  font-family: var(--font-mono);
  font-size: 13px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--ink-soft);
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--rule);
}
.month-stat { margin-bottom: 8px; }
.month-stat .ms-label {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--ink-faint);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.month-stat .ms-val {
  font-family: var(--font-serif);
  font-size: 24px;
  font-weight: 500;
  color: var(--ink-strong);
  line-height: 1.1;
  font-variation-settings: "opsz" 30;
}
.ms-delta {
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 600;
}
.ms-delta.up   { color: var(--green); }
.ms-delta.down { color: var(--red); }

/* Region cards for POSB */
.reg-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 18px;
}
.reg-card {
  background: var(--paper-warm);
  border: 1px solid var(--rule);
  padding: 16px 20px;
  border-top: 3px solid var(--rule-strong);
}
.reg-card.knl { border-top-color: oklch(0.46 0.10 245); }
.reg-card.vja { border-top-color: var(--green); }
.reg-card.vsp { border-top-color: var(--accent); }
.reg-card h4 {
  font-family: var(--font-mono);
  font-size: 13px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--ink-soft);
  margin-bottom: 8px;
}
.reg-card .rc-stat {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 4px;
  font-size: 14px;
}
.rc-label { color: var(--ink-soft); font-family: var(--font-mono); font-size: 12px; letter-spacing: 0.06em; }
.rc-val { font-family: var(--font-serif); font-size: 18px; font-weight: 500; color: var(--ink-strong); }
.rc-net-pos { font-family: var(--font-serif); font-size: 22px; font-weight: 600; color: var(--green); }
.rc-net-neg { font-family: var(--font-serif); font-size: 22px; font-weight: 600; color: var(--red); }

/* Procurement rate bar */
.proc-rate-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 5px;
}
.proc-rate-label { font-family: var(--font-mono); font-size: 13px; width: 180px; color: var(--ink-soft); }
.proc-rate-track { flex: 1; height: 14px; background: var(--paper-warm); border-radius: 2px; overflow: hidden; }
.proc-rate-fill  { height: 100%; border-radius: 2px; background: var(--accent); }
.proc-rate-pct   { font-family: var(--font-mono); font-size: 13px; width: 45px; text-align: right; color: var(--ink); }

/* Two-column layout for insurance details */
.ins-two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 18px;
}

/* Period note badge */
.period-note {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: 13px;
  background: var(--amber-pale);
  border: 1px solid var(--amber);
  color: var(--ink-soft);
  padding: 4px 10px;
  border-radius: 3px;
  letter-spacing: 0.06em;
  margin-bottom: 14px;
}
"""

# ─── 5. NEW RENDER JAVASCRIPT ─────────────────────────────────────────────────

RENDER_JS = r"""
// ============ POSB / PLI / RPLI RENDER FUNCTIONS ============

function fmtLakh(n) {
  if (n >= 1e7) return (n/1e7).toFixed(2) + ' Cr';
  if (n >= 1e5) return (n/1e5).toFixed(2) + ' L';
  return fmtInt(n);
}

function getPeriodKey() {
  const from = document.getElementById('month-from').value;
  const to   = document.getElementById('month-to').value;
  return { from, to };
}

function getInsData(table, from, to, divKey) {
  var apr = (table['Apr-26'] || {})[divKey] || {};
  var may = (table['May-26'] || {})[divKey] || {};
  // APR-26 only
  if (from === 'Apr-26' && to === 'Apr-26') return { data: apr, period: 'April 2026' };
  // MAY-26 only → cumulative May minus April
  if (from === 'May-26' && to === 'May-26') {
    var onlyMay = Object.assign({}, may, {
      policies: (may.policies || 0) - (apr.policies || 0),
      premium:  (may.premium  || 0) - (apr.premium  || 0),
      offices_procured: may.offices_procured || 0,
      total_offices: may.total_offices || 0,
      avg_premium: ((may.policies||0)-(apr.policies||0)) > 0
        ? Math.round(((may.premium||0)-(apr.premium||0)) / ((may.policies||0)-(apr.policies||0))) : 0,
      procurement_rate: may.procurement_rate || 0,
    });
    return { data: onlyMay, period: 'May 2026 only' };
  }
  // Range Apr-May: use May cumulative
  return { data: may, period: 'Apr–May 2026 (cumulative)' };
}

function renderPOSBTab(d, divName) {
  const isCircle = !divName || divName === '__CIRCLE__' || (d && d.isAggregate);

  // ── Accounts section ──
  var accEl = document.getElementById('posb-accounts-content');
  if (!accEl) return;

  var key = isCircle ? '__CIRCLE__' : divName;
  var pa  = POSB_ACTUALS[key] || null;

  if (pa) {
    var circlePA = POSB_ACTUALS['__CIRCLE__'] || {};
    var circleNet = circlePA.net || 1;
    var netCls = pa.net >= 0 ? 'green-bg' : 'red-bg';
    var netCol = pa.net >= 0 ? 'var(--green)' : 'var(--red)';
    var pct   = pa.opened > 0 ? (pa.closed / pa.opened * 100).toFixed(1) : 0;

    var kpiHtml = `
      <div class="period-note">Data period: 01-Apr-2026 to 31-May-2026 (two-month cumulative)</div>
      <div class="ins-kpi-strip cols-4">
        <div class="ins-kpi feature">
          <div class="ins-kpi-label">Net Addition</div>
          <div class="ins-kpi-value" style="color:${pa.net>=0?'var(--accent)':'oklch(0.78 0.05 25)'};">${pa.net>=0?'+':''}${fmtInt(pa.net)}</div>
          <div class="ins-kpi-sub">${isCircle?'Circle total':'Division total'} · ${pa.net >= 0 ? 'Net positive ✓' : 'Net negative ✗'}</div>
        </div>
        <div class="ins-kpi">
          <div class="ins-kpi-label">Accounts Opened</div>
          <div class="ins-kpi-value">${fmtInt(pa.opened)}</div>
          <div class="ins-kpi-sub">In 2-month period</div>
        </div>
        <div class="ins-kpi">
          <div class="ins-kpi-label">Accounts Closed</div>
          <div class="ins-kpi-value">${fmtInt(pa.closed)}</div>
          <div class="ins-kpi-sub">Closure rate: ${pct}% of opened</div>
        </div>
        <div class="ins-kpi">
          <div class="ins-kpi-label">Offices in scope</div>
          <div class="ins-kpi-value">${fmtInt(pa.offices)}</div>
          <div class="ins-kpi-sub">${isCircle ? 'Circle-wide' : 'In this division'}</div>
        </div>
      </div>`;

    // Regional breakdown for circle view
    if (isCircle) {
      var regs = [
        { key: '__REG_Vijayawada__',    label: 'Vijayawada Region',    cls: 'vja' },
        { key: '__REG_Kurnool__',       label: 'Kurnool Region',       cls: 'knl' },
        { key: '__REG_Visakhapatnam__', label: 'Visakhapatnam Region', cls: 'vsp' },
      ];
      kpiHtml += '<div class="reg-cards">';
      regs.forEach(function(r) {
        var rp = POSB_ACTUALS[r.key] || {};
        var netHtml = rp.net >= 0
          ? `<span class="rc-net-pos">+${fmtInt(rp.net)}</span>`
          : `<span class="rc-net-neg">${fmtInt(rp.net)}</span>`;
        kpiHtml += `
          <div class="reg-card ${r.cls}">
            <h4>${r.label}</h4>
            <div class="rc-stat"><span class="rc-label">Opened</span><span class="rc-val">${fmtInt(rp.opened)}</span></div>
            <div class="rc-stat"><span class="rc-label">Closed</span><span class="rc-val">${fmtInt(rp.closed)}</span></div>
            <div class="rc-stat"><span class="rc-label">Net Addition</span>${netHtml}</div>
            <div class="rc-stat"><span class="rc-label">Offices</span><span style="font-size:14px;color:var(--ink-soft);">${fmtInt(rp.offices)}</span></div>
          </div>`;
      });
      kpiHtml += '</div>';

      // Division performance bars sorted by Net Addition
      var divRows = POSB_RAW_JS
        .slice().sort(function(a,b){ return b.net - a.net; });
      var maxAbs = Math.max(...divRows.map(function(r){ return Math.abs(r.net); }), 1);

      kpiHtml += '<div class="section-head" style="margin-top:28px; margin-bottom:12px;">' +
        '<h2>Division-wise Net Addition — ranked</h2>' +
        '<span class="desc">Apr–May 2026 · 29 divisions<br>Green = positive · Red = negative</span></div>';
      kpiHtml += '<div class="ins-div-bars">';
      divRows.forEach(function(r, i) {
        var w = Math.abs(r.net) / maxAbs * 100;
        var cls = r.net >= 0 ? 'pos' : 'neg';
        var valSign = r.net >= 0 ? '+' : '';
        var regAbbr = r.region === 'Vijayawada' ? 'VJA' : r.region === 'Kurnool' ? 'KNL' : 'VSP';
        kpiHtml += `
          <div class="ins-bar-row">
            <div class="ins-bar-name">${String(i+1).padStart(2,'0')}. ${r.name}
              <span class="region-tag">${regAbbr}</span></div>
            <div class="ins-bar-track">
              <div class="ins-bar-fill ${cls}" style="width:${w.toFixed(1)}%;"></div>
            </div>
            <div class="ins-bar-val ${cls}">${valSign}${fmtInt(r.net)}</div>
            <div class="ins-bar-sub">${fmtInt(r.opened)} / ${fmtInt(r.closed)}</div>
          </div>`;
      });
      kpiHtml += '</div>';
    }

    accEl.innerHTML = kpiHtml;
  } else {
    accEl.innerHTML = '<div class="placeholder"><strong>No POSB activity data</strong>This unit does not operate POSB services.</div>';
  }

  // ── Targets section ──
  var tgtEl = document.getElementById('posb-targets-content');
  if (!tgtEl) return;
  // Reuse existing renderFinancial logic for targets
  var posbEl2 = tgtEl;
  if (d && d.posb_tgt) {
    var t = d.posb_tgt;
    var h = d.posb_hist;
    var monthlyAdds = t.net_add_target_FY27 / 12;
    var ytdNet = pa ? pa.net : 0;
    var ytdPace = monthlyAdds > 0 ? (ytdNet / (monthlyAdds * 2) * 100).toFixed(1) : '—';
    var paceCls = ytdNet >= monthlyAdds * 2 ? 'green' : ytdNet >= monthlyAdds ? 'amber' : 'red';
    posbEl2.innerHTML = `
      <div class="ins-kpi-strip cols-4">
        <div class="ins-kpi feature">
          <div class="ins-kpi-label">Live Accounts Base (01-Apr-26)</div>
          <div class="ins-kpi-value">${fmtInt(t.live_accounts)}</div>
          <div class="ins-kpi-sub">@ ₹219.23/yr each = ₹${fmt(t.live_revenue,2)} Cr revenue</div>
        </div>
        <div class="ins-kpi">
          <div class="ins-kpi-label">Silent Accounts</div>
          <div class="ins-kpi-value">${fmtInt(t.silent_accounts)}</div>
          <div class="ins-kpi-sub">@ ₹35.61 = ₹${fmt(t.silent_revenue,2)} Cr (booked Apr)</div>
        </div>
        <div class="ins-kpi">
          <div class="ins-kpi-label">FY 2026-27 Net Add Target</div>
          <div class="ins-kpi-value">${fmtInt(t.net_add_target_FY27)}</div>
          <div class="ins-kpi-sub">Monthly pace: ${fmtInt(Math.round(monthlyAdds))}/month</div>
        </div>
        <div class="ins-kpi ${paceCls==='green'?'green-bg':paceCls==='amber'?'amber-bg':'red-bg'}">
          <div class="ins-kpi-label">YTD Pace (Apr+May)</div>
          <div class="ins-kpi-value" style="color:${paceCls==='green'?'var(--green)':paceCls==='amber'?'var(--amber)':'var(--red)'};">${ytdPace}%</div>
          <div class="ins-kpi-sub">Net ${pa?fmtInt(ytdNet):'—'} vs target ${fmtInt(Math.round(monthlyAdds*2))}</div>
        </div>
      </div>`;
    if (h && h.fy26_pct_ach < 80) {
      posbEl2.innerHTML += `<div class="caveat"><strong>FY25-26 historical flag —</strong> Only ${fmt(h.fy26_pct_ach,1)}% of FY25-26 net add target achieved. FY 2026-27 target: ${fmtInt(t.net_add_target_FY27)}. Early intervention needed.</div>`;
    }
  } else {
    posbEl2.innerHTML = '<div class="placeholder"><strong>No POSB target data</strong>This unit (typically RMS) does not handle POSB operations.</div>';
  }
}

function renderInsuranceTab(tabKey, tableConst, fromMonth, toMonth, divName, d) {
  var isCircle = !divName || divName === '__CIRCLE__' || (d && d.isAggregate);
  var divKey   = isCircle ? '__CIRCLE__' : divName;
  var isPLI    = tabKey === 'pli';
  var label    = isPLI ? 'PLI' : 'RPLI';
  var fullLabel= isPLI ? 'Postal Life Insurance' : 'Rural Postal Life Insurance';

  var kpiEl = document.getElementById(tabKey + '-kpi-content');
  var divEl = document.getElementById(tabKey + '-div-content');
  if (!kpiEl || !divEl) return;

  var prd  = getInsData(tableConst, fromMonth, toMonth, divKey);
  var aprD = (tableConst['Apr-26'] || {})[divKey] || {};
  var mayD = (tableConst['May-26'] || {})[divKey] || {};
  var cur  = prd.data;
  var period = prd.period;

  // KPI strip
  var procRate = cur.procurement_rate || 0;
  var procCls  = procRate >= 30 ? 'green-bg' : procRate >= 15 ? 'amber-bg' : 'red-bg';
  var cL = isPLI ? (d && d.pli ? d.pli.tbp_target : 0) : (d && d.rpli ? d.rpli.tbp_target : 0);

  kpiEl.innerHTML = `
    <div class="period-note">Showing: ${period}</div>
    <div class="ins-kpi-strip cols-4">
      <div class="ins-kpi feature">
        <div class="ins-kpi-label">${label} — Policies Procured</div>
        <div class="ins-kpi-value">${fmtInt(cur.policies || 0)}</div>
        <div class="ins-kpi-sub">${fullLabel}</div>
      </div>
      <div class="ins-kpi">
        <div class="ins-kpi-label">Premium Collected</div>
        <div class="ins-kpi-value">${fmtLakh(cur.premium || 0)}</div>
        <div class="ins-kpi-sub">₹${fmtInt(cur.avg_premium || 0)} avg per policy</div>
      </div>
      <div class="ins-kpi ${procCls}">
        <div class="ins-kpi-label">Procurement Rate</div>
        <div class="ins-kpi-value">${fmt(procRate,1)}<span style="font-size:18px;">%</span></div>
        <div class="ins-kpi-sub">${fmtInt(cur.offices_procured||0)} of ${fmtInt(cur.total_offices||0)} offices</div>
      </div>
      <div class="ins-kpi">
        <div class="ins-kpi-label">FY 2026-27 TBP Target</div>
        <div class="ins-kpi-value">${cL > 0 ? '₹'+fmt(cL,2)+' Cr' : '—'}</div>
        <div class="ins-kpi-sub">${cL > 0 ? 'Monthly pace: ₹'+fmt(cL/12,3)+' Cr' : 'No target data'}</div>
      </div>
    </div>`;

  // Month comparison panel
  var mayOnlyPols = (mayD.policies||0) - (aprD.policies||0);
  var mayOnlyPrem = (mayD.premium||0)  - (aprD.premium||0);
  var mayOnlyAvg  = mayOnlyPols > 0 ? Math.round(mayOnlyPrem / mayOnlyPols) : 0;
  kpiEl.innerHTML += `
    <div class="month-compare">
      <div class="month-col header">
        <h4>April 2026</h4>
        <div class="month-stat"><div class="ms-label">Policies</div><div class="ms-val">${fmtInt(aprD.policies||0)}</div></div>
        <div class="month-stat"><div class="ms-label">Premium</div><div class="ms-val">${fmtLakh(aprD.premium||0)}</div></div>
        <div class="month-stat"><div class="ms-label">Offices Procured</div><div class="ms-val">${fmtInt(aprD.offices_procured||0)}</div></div>
        <div class="month-stat"><div class="ms-label">Proc. Rate</div><div class="ms-val">${fmt(aprD.procurement_rate||0,1)}%</div></div>
        <div class="month-stat"><div class="ms-label">Avg Premium</div><div class="ms-val">₹${fmtInt(aprD.avg_premium||0)}</div></div>
      </div>
      <div class="month-col">
        <h4>May 2026 (month-only)</h4>
        <div class="month-stat"><div class="ms-label">Policies</div><div class="ms-val">${fmtInt(mayOnlyPols)}</div></div>
        <div class="month-stat"><div class="ms-label">Premium</div><div class="ms-val">${fmtLakh(mayOnlyPrem)}</div></div>
        <div class="month-stat"><div class="ms-label">Offices Procured</div><div class="ms-val">${fmtInt(mayD.offices_procured||0)}</div></div>
        <div class="month-stat"><div class="ms-label">Proc. Rate</div><div class="ms-val">${fmt(mayD.procurement_rate||0,1)}%</div></div>
        <div class="month-stat"><div class="ms-label">Avg Premium</div><div class="ms-val">₹${fmtInt(mayOnlyAvg)}</div></div>
      </div>
      <div class="month-col">
        <h4>Apr+May Cumulative</h4>
        <div class="month-stat"><div class="ms-label">Policies</div>
          <div class="ms-val">${fmtInt(mayD.policies||0)}</div>
          <div class="ms-delta ${mayOnlyPols > (aprD.policies||0) ? 'up' : 'down'}">
            ${mayOnlyPols > (aprD.policies||0) ? '▲ ' : '▼ '}${mayOnlyPols > (aprD.policies||0)
              ? '+'+fmtInt(mayOnlyPols-(aprD.policies||0)) : fmtInt(mayOnlyPols-(aprD.policies||0))} vs Apr</div>
        </div>
        <div class="month-stat"><div class="ms-label">Premium</div>
          <div class="ms-val">${fmtLakh(mayD.premium||0)}</div>
          <div class="ms-delta ${mayOnlyPrem > (aprD.premium||0) ? 'up' : 'down'}">
            ${mayOnlyPrem > (aprD.premium||0) ? '▲' : '▼'} ${fmtLakh(Math.abs(mayOnlyPrem - (aprD.premium||0)))}</div>
        </div>
        <div class="month-stat"><div class="ms-label">Offices Procured</div>
          <div class="ms-val">${fmtInt(mayD.offices_procured||0)}</div>
          <div class="ms-delta ${(mayD.offices_procured||0)>(aprD.offices_procured||0)?'up':'down'}">
            ${(mayD.offices_procured||0)>(aprD.offices_procured||0)?'▲ +':'▼ '}${fmtInt((mayD.offices_procured||0)-(aprD.offices_procured||0))} vs Apr</div>
        </div>
        <div class="month-stat"><div class="ms-label">Proc. Rate</div><div class="ms-val">${fmt(mayD.procurement_rate||0,1)}%</div></div>
      </div>
    </div>`;

  // Division bars (circle/region view)
  if (isCircle) {
    var rawData = isPLI ? PLI_RAW_JS : RPLI_RAW_JS;
    var rawDataApr = isPLI ? PLI_APR_JS : RPLI_APR_JS;
    var rawDataMay = isPLI ? PLI_MAY_JS : RPLI_MAY_JS;

    // Determine which data to show based on period
    var showData;
    if (fromMonth === 'Apr-26' && toMonth === 'Apr-26') {
      showData = rawDataApr.map(function(r){ return Object.assign({},r); });
    } else if (fromMonth === 'May-26' && toMonth === 'May-26') {
      // May-only
      var aprMap = {};
      rawDataApr.forEach(function(r){ aprMap[r.name] = r; });
      showData = rawDataMay.map(function(r){
        var a = aprMap[r.name] || {policies:0, premium:0};
        return Object.assign({},r,{
          policies: r.policies - (a.policies||0),
          premium:  r.premium  - (a.premium||0),
        });
      });
    } else {
      showData = rawDataMay.map(function(r){ return Object.assign({},r); });
    }

    // Sort by policies descending for display
    showData.sort(function(a,b){ return b.premium - a.premium; });
    var maxPol = Math.max.apply(null, showData.map(function(r){ return r.policies||0; })) || 1;
    var maxPrem = Math.max.apply(null, showData.map(function(r){ return r.premium||0; })) || 1;

    divEl.innerHTML = '<div class="ins-div-bars">';
    showData.forEach(function(r, i) {
      var w = (r.policies||0) / maxPol * 100;
      var procR = r.offices_procured > 0
        ? (r.offices_procured / (r.total_offices||1) * 100) : 0;
      var barCls = procR >= 30 ? 'hi' : procR >= 15 ? 'med' : 'lo';
      var regA = r.region === 'Vijayawada' ? 'VJA' : r.region === 'Kurnool' ? 'KNL' : 'VSP';
      divEl.innerHTML += `
        <div class="ins-bar-row">
          <div class="ins-bar-name">${String(i+1).padStart(2,'0')}. ${r.name}
            <span class="region-tag">${regA}</span></div>
          <div class="ins-bar-track">
            <div class="ins-bar-fill ${barCls}" style="width:${w.toFixed(1)}%;" title="${fmtInt(r.policies||0)} policies"></div>
          </div>
          <div class="ins-bar-val">${fmtInt(r.policies||0)} pol</div>
          <div class="ins-bar-sub">₹${fmtLakh(r.premium||0)}</div>
        </div>`;
    });
    divEl.innerHTML += '</div>';

    // Procurement rate section
    var procRows = showData.slice().sort(function(a,b){
      var rA = a.offices_procured/(a.total_offices||1);
      var rB = b.offices_procured/(b.total_offices||1);
      return rB - rA;
    });
    var maxProc = 100;
    divEl.innerHTML += '<div class="section-head" style="margin-top:24px; margin-bottom:10px;"><h2>Procurement Rate by Division</h2><span class="desc">% of offices with ≥1 policy · sorted highest first</span></div>';
    procRows.forEach(function(r) {
      var pr = r.offices_procured / (r.total_offices||1) * 100;
      divEl.innerHTML += `
        <div class="proc-rate-row">
          <div class="proc-rate-label">${r.name}</div>
          <div class="proc-rate-track">
            <div class="proc-rate-fill" style="width:${pr.toFixed(1)}%; background:${pr>=30?'var(--green)':pr>=15?'var(--amber)':'var(--red)'};"></div>
          </div>
          <div class="proc-rate-pct">${fmt(pr,1)}%</div>
        </div>`;
    });
  } else {
    // Division-specific view
    var divPLI = isPLI ? d.pli : d.rpli;
    var html = '';
    if (divPLI) {
      var tbpAch = cur.premium || 0;
      var tbpPro = divPLI.tbp_target / 12;
      var pctTgt = tbpPro > 0 ? (tbpAch / 100000 / tbpPro * 100).toFixed(1) : '—';
      html += `
        <div class="ins-kpi-strip cols-3" style="margin-top:16px;">
          <div class="ins-kpi">
            <div class="ins-kpi-label">TBP Target (FY 2026-27)</div>
            <div class="ins-kpi-value">₹${fmt(divPLI.tbp_target,2)} Cr</div>
            <div class="ins-kpi-sub">Monthly pace: ₹${fmt(divPLI.tbp_target/12,3)} Cr</div>
          </div>
          <div class="ins-kpi">
            <div class="ins-kpi-label">NBP Target</div>
            <div class="ins-kpi-value">₹${fmt(divPLI.nbp_target,2)} Cr</div>
            <div class="ins-kpi-sub">New business premium</div>
          </div>
          <div class="ins-kpi">
            <div class="ins-kpi-label">Sales Force</div>
            <div class="ins-kpi-value">${fmtInt(divPLI.sales_force)}</div>
            <div class="ins-kpi-sub">Registered agents</div>
          </div>
        </div>`;
    }
    divEl.innerHTML = html || '<div class="placeholder">No division-level breakdown available.</div>';
  }
}

function renderPLITab(d, divName) {
  var p = getPeriodKey();
  renderInsuranceTab('pli', PLI_POLICIES, p.from, p.to, divName, d);
}

function renderRPLITab(d, divName) {
  var p = getPeriodKey();
  renderInsuranceTab('rpli', RPLI_POLICIES, p.from, p.to, divName, d);
}
// ============ END POSB / PLI / RPLI ============
"""

# ─── 6. NEW HTML TAB CONTENT ──────────────────────────────────────────────────

NEW_TAB_BUTTONS = """\
  <button class="tab" onclick="showTab('posb', this)">POSB</button>
  <button class="tab" onclick="showTab('pli', this)">PLI</button>
  <button class="tab" onclick="showTab('rpli', this)">RPLI</button>"""

NEW_TAB_CONTENT = """\
<!-- ===== POSB TAB ===== -->
<div id="tab-posb" class="tab-content">
  <div class="section-head">
    <h2>POSB — Account Activity · Apr–May 2026</h2>
    <span class="desc">Accounts Opened · Closed · Net Addition<br>01-Apr-2026 to 31-May-2026</span>
  </div>
  <div id="posb-accounts-content"></div>

  <div class="section-head" style="margin-top: 32px;">
    <h2>POSB — Account Base &amp; FY 2026-27 Target</h2>
    <span class="desc">Live accounts · Silent · Net add target<br>FY25-26 historical performance</span>
  </div>
  <div id="posb-targets-content"></div>
</div>

<!-- ===== PLI TAB ===== -->
<div id="tab-pli" class="tab-content">
  <div class="section-head">
    <h2>PLI — Policies Procured &amp; Premium</h2>
    <span class="desc">Postal Life Insurance · Division-wise<br>Use month selector above to change period</span>
  </div>
  <div id="pli-kpi-content"></div>
  <div class="section-head" style="margin-top:28px; margin-bottom:12px;">
    <h2>Division-wise PLI performance</h2>
    <span class="desc">Policies procured · Premium collected<br>Bar width = policies · colour = procurement rate</span>
  </div>
  <div id="pli-div-content"></div>
</div>

<!-- ===== RPLI TAB ===== -->
<div id="tab-rpli" class="tab-content">
  <div class="section-head">
    <h2>RPLI — Policies Procured &amp; Premium</h2>
    <span class="desc">Rural Postal Life Insurance · Division-wise<br>Use month selector above to change period</span>
  </div>
  <div id="rpli-kpi-content"></div>
  <div class="section-head" style="margin-top:28px; margin-bottom:12px;">
    <h2>Division-wise RPLI performance</h2>
    <span class="desc">Policies procured · Premium collected<br>Bar width = policies · colour = procurement rate</span>
  </div>
  <div id="rpli-div-content"></div>
</div>"""

# ─── 7. PATCH index.html ─────────────────────────────────────────────────────

def build_raw_js_array(raw):
    """Convert raw list to a JSON array of objects for use in JS render functions."""
    items = []
    for r in raw:
        items.append({
            "name": r[0], "total_offices": r[1], "offices_procured": r[2],
            "policies": r[3], "premium": r[4], "region": r[5],
            "procurement_rate": round(r[2]/r[1]*100,1) if r[1]>0 else 0,
        })
    return json.dumps(items, ensure_ascii=False)

def build_posb_raw_js(raw):
    items = []
    for r in raw:
        items.append({
            "name": r[0], "offices": r[1], "opened": r[2],
            "closed": r[3], "net": r[4], "region": r[5],
        })
    return json.dumps(items, ensure_ascii=False)

def patch_html(may_booking_js):
    print("Reading index.html...")
    with open(HTML, encoding='utf-8') as f:
        html = f.read()

    # ── a. Add CSS before </style> ──
    css_marker = '</style>'
    if 'ins-kpi-strip' not in html:
        idx = html.rfind(css_marker)
        if idx == -1:
            print("ERROR: Could not find </style>")
            return
        html = html[:idx] + NEW_CSS + '\n' + html[idx:]
        print("  ✓ Injected new CSS")
    else:
        print("  ⚡ CSS already present, skipping")

    # ── b. Build JS data constants ──
    js_constants = f"""
// ============ PLI / RPLI / POSB MONTHLY DATA (auto-generated) ============
const PLI_POLICIES  = {json.dumps(PLI_POLICIES,  ensure_ascii=False)};
const RPLI_POLICIES = {json.dumps(RPLI_POLICIES, ensure_ascii=False)};
const POSB_ACTUALS  = {json.dumps(POSB_ACTUALS,  ensure_ascii=False)};
// Raw arrays for bar-chart rendering
const PLI_APR_JS  = {build_raw_js_array(PLI_APR_RAW)};
const PLI_MAY_JS  = {build_raw_js_array(PLI_MAY_RAW)};
const PLI_RAW_JS  = PLI_MAY_JS;
const RPLI_APR_JS = {build_raw_js_array(RPLI_APR_RAW)};
const RPLI_MAY_JS = {build_raw_js_array(RPLI_MAY_RAW)};
const RPLI_RAW_JS = RPLI_MAY_JS;
const POSB_RAW_JS = {build_posb_raw_js(POSB_RAW)};
// ============ END AUTO-GENERATED ============
"""

    # Inject after REG_ABBR constant
    reg_abbr_pattern = r"(const REG_ABBR = \{[^\}]+\};)"
    if 'PLI_POLICIES' not in html:
        html, n = re.subn(reg_abbr_pattern, r'\1\n' + js_constants, html, count=1)
        if n:
            print("  ✓ Injected PLI/RPLI/POSB constants")
        else:
            print("  ERROR: Could not find REG_ABBR insertion point")
    else:
        print("  ⚡ PLI_POLICIES already present, replacing...")
        html = re.sub(
            r'// ============ PLI / RPLI / POSB MONTHLY DATA.*?// ============ END AUTO-GENERATED ============\n',
            js_constants, html, flags=re.DOTALL
        )

    # ── c. Inject DATA_BY_MONTH['May-26'] ──
    if "DATA_BY_MONTH['May-26']" not in html:
        # Find end of PLI_RPLI_PATCH block
        patch_marker = r"(Object\.entries\(PLI_RPLI_PATCH\)\.forEach.*?\}\);)"
        may_block = '\n\n// ─── May-26 snapshot ───\n' + may_booking_js + '\n'
        html, n = re.subn(patch_marker, r'\1' + may_block, html, count=1, flags=re.DOTALL)
        if n:
            print("  ✓ Injected DATA_BY_MONTH['May-26']")
        else:
            # Try simpler insertion after DATA_BY_MONTH definition line
            dbm_line = "const DATA_BY_MONTH ="
            idx = html.find(dbm_line)
            if idx > -1:
                # Find the end of this const (the matching ';')
                end = html.find('};', idx)
                if end > -1:
                    html = html[:end+2] + may_block + html[end+2:]
                    print("  ✓ Injected DATA_BY_MONTH['May-26'] (alt method)")
    else:
        print("  ⚡ DATA_BY_MONTH['May-26'] already present")

    # ── d. Replace tab button for 'financial' with POSB / PLI / RPLI ──
    old_fin_btn = r'<button class="tab" onclick="showTab\(\'financial\', this\)">POSB &amp; Insurance</button>'
    new_fin_btns = (
        '<button class="tab" onclick="showTab(\'posb\', this)">POSB</button>\n'
        '  <button class="tab" onclick="showTab(\'pli\', this)">PLI</button>\n'
        '  <button class="tab" onclick="showTab(\'rpli\', this)">RPLI</button>'
    )
    if 'showTab(\'posb\'' not in html:
        html, n = re.subn(old_fin_btn, new_fin_btns, html)
        if n:
            print("  ✓ Updated tab buttons")
        else:
            print("  WARNING: Could not replace tab button — trying literal match")
            html = html.replace(
                "<button class=\"tab\" onclick=\"showTab('financial', this)\">POSB &amp; Insurance</button>",
                "<button class=\"tab\" onclick=\"showTab('posb', this)\">POSB</button>\n"
                "  <button class=\"tab\" onclick=\"showTab('pli', this)\">PLI</button>\n"
                "  <button class=\"tab\" onclick=\"showTab('rpli', this)\">RPLI</button>"
            )
    else:
        print("  ⚡ POSB tab button already present")

    # ── e. Replace tab-financial content div ──
    old_financial_div = r'<!-- ===== POSB & INSURANCE TAB ===== -->.*?</div>\s*\n\s*<!-- ====='
    if 'id="tab-posb"' not in html:
        match = re.search(r'<!-- ===== POSB &amp; INSURANCE TAB ===== -->.*?(?=<!-- =====)', html, re.DOTALL)
        if match:
            html = html[:match.start()] + NEW_TAB_CONTENT + '\n\n' + html[match.end():]
            print("  ✓ Replaced tab-financial with POSB/PLI/RPLI tabs")
        else:
            # Try matching the original section
            match2 = re.search(r'<!-- ===== POSB & INSURANCE TAB ===== -->.*?(?=<!-- =====)', html, re.DOTALL)
            if match2:
                html = html[:match2.start()] + NEW_TAB_CONTENT + '\n\n' + html[match2.end():]
                print("  ✓ Replaced POSB & INSURANCE tab (alt match)")
            else:
                # Try finding the div by id
                match3 = re.search(r'<div id="tab-financial"[^>]*>.*?</div>\s*\n\s*(?=<!-- ===== SERVICE)', html, re.DOTALL)
                if match3:
                    html = html[:match3.start()] + NEW_TAB_CONTENT + '\n\n' + html[match3.end():]
                    print("  ✓ Replaced tab-financial div")
                else:
                    print("  WARNING: Could not replace financial tab content")
    else:
        print("  ⚡ POSB/PLI/RPLI tabs already present")

    # ── f. Inject render functions before closing </script> ──
    if 'renderPOSBTab' not in html:
        # Find renderFinancial function and replace it
        rf_pattern = r'function renderFinancial\(d\).*?^}'
        match = re.search(rf_pattern, html, re.DOTALL | re.MULTILINE)
        if match:
            html = html[:match.start()] + RENDER_JS.strip() + html[match.end():]
            print("  ✓ Replaced renderFinancial with new render functions")
        else:
            # Inject before the last </script>
            last_script = html.rfind('</script>')
            if last_script > -1:
                html = html[:last_script] + '\n' + RENDER_JS + '\n' + html[last_script:]
                print("  ✓ Injected render functions before </script>")
    else:
        print("  ⚡ renderPOSBTab already present")

    # ── g. Update renderDivision call to use new functions ──
    old_call = 'renderFinancial(d);'
    new_call = (
        'renderPOSBTab(d, divName);\n'
        '  renderPLITab(d, divName);\n'
        '  renderRPLITab(d, divName);'
    )
    if 'renderPOSBTab' in html and old_call in html:
        html = html.replace(old_call, new_call, 1)
        print("  ✓ Updated renderDivision call")
    elif old_call not in html:
        print("  ⚡ renderFinancial call already replaced")

    # ── h. Update title ──
    html = html.replace(
        'Division Health Card · AP Circle · April 2026',
        'Division Health Card · AP Circle · FY 2026-27'
    )

    print("Writing updated index.html...")
    with open(HTML, 'w', encoding='utf-8') as f:
        f.write(html)
    print("  ✓ Done!")

# ─── MAIN ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("=== patch_may2026.py ===\n")

    print("Step 1: Loading office hierarchy...")
    hierarchy = load_hierarchy()
    print(f"  Loaded {len(hierarchy):,} office entries")

    print("Step 2: Processing May booking data from CSVs...")
    may_bk = process_may_booking(hierarchy)
    print(f"  Aggregated booking for {len(may_bk)} divisions")

    print("Step 3: Building May-26 DATA_BY_MONTH injection...")
    may26_js = build_may26_injection(APR_BK, may_bk)
    print("  Built May-26 snapshot JS")

    print("Step 4: Patching index.html...")
    patch_html(may26_js)

    print("\n=== All done! ===")
    print("Open index.html in a browser to verify.")
