"""
Build _subdiv_booking.json
Maps: division -> sub_division -> { HOs, SOs, BOs } with April 2026 article & revenue totals.
"""
import json, csv, re
from collections import defaultdict
import openpyxl

BASE = r"c:\Users\Bhargavi\Documents\Division_Health_Report\Division_Health_Report"
HIER_XLSX = BASE + r"\uploads\Hierarchy_data.xlsx"
BOOKING_CSV = BASE + r"\uploads\booking_productwise.csv"
OUT_JSON = BASE + r"\_subdiv_booking.json"

# ── 1. Load hierarchy ──────────────────────────────────────────────────────────
print("Loading hierarchy...")
wb = openpyxl.load_workbook(HIER_XLSX, read_only=True, data_only=True)
ws = wb["Worksheet"]
rows = list(ws.iter_rows(values_only=True))
headers = [str(h).strip() if h else "" for h in rows[0]]
col = {h: i for i, h in enumerate(headers)}

INCLUDE_TYPES = {"HPO", "SPO", "BPO"}  # HO, SO, BO

hier = {}  # office_id -> record
for row in rows[1:]:
    oid  = str(row[col["office_id"]]).strip() if row[col["office_id"]] else ""
    otype = str(row[col["office_type_code"]]).strip() if row[col["office_type_code"]] else ""
    if not oid or otype not in INCLUDE_TYPES:
        continue
    div   = str(row[col["division_name"]]).strip().replace(" Division","").replace(" division","") if row[col["division_name"]] else ""
    subdiv = str(row[col["sub_division_name"]]).strip().replace(" Sub Division","").replace(" Sub division","").replace(" sub division","") if row[col["sub_division_name"]] else ""
    name  = str(row[col["office_name"]]).strip() if row[col["office_name"]] else ""
    hier[oid] = {
        "name": name,
        "type": otype,          # HPO / SPO / BPO
        "division": div,
        "sub_division": subdiv,
    }

print(f"  {len(hier)} offices (HPO+SPO+BPO) loaded")
wb.close()

# ── 2. Aggregate booking data ──────────────────────────────────────────────────
print("Aggregating booking CSV...")
office_agg = defaultdict(lambda: {"articles": 0, "revenue": 0.0})

def clean_num(v):
    if v is None: return 0.0
    s = str(v).replace(",","").replace(" ","").strip()
    try: return float(s)
    except: return 0.0

with open(BOOKING_CSV, encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        oid = str(row.get("office-id","")).strip()
        if not oid or oid == "-":
            continue
        arts = clean_num(row.get("article-count", 0))
        rev  = clean_num(row.get("total_amount", 0))
        office_agg[oid]["articles"] += arts
        office_agg[oid]["revenue"]  += rev

print(f"  {len(office_agg)} offices found in booking CSV")

# ── 3. Merge and build structure ───────────────────────────────────────────────
# structure: { division: { sub_division: { HOs:[], SOs:[], BOs:[] } } }
print("Building structure...")

TYPE_MAP = {"HPO": "HOs", "SPO": "SOs", "BPO": "BOs"}

structure = defaultdict(lambda: defaultdict(lambda: {"HOs": [], "SOs": [], "BOs": []}))

for oid, info in hier.items():
    div    = info["division"]
    subdiv = info["sub_division"]
    slot   = TYPE_MAP[info["type"]]
    bk     = office_agg.get(oid, {"articles": 0, "revenue": 0.0})
    structure[div][subdiv][slot].append({
        "id":       oid,
        "name":     info["name"],
        "articles": int(round(bk["articles"])),
        "revenue":  round(bk["revenue"], 2),
    })

# Sort each list by articles ascending (NIL first — makes improvement targets easy to find)
for div in structure:
    for subdiv in structure[div]:
        for slot in ("HOs","SOs","BOs"):
            structure[div][subdiv][slot].sort(key=lambda x: x["articles"])

# Convert defaultdicts to plain dicts
out = {}
for div, subdivs in sorted(structure.items()):
    out[div] = {}
    for sd, slots in sorted(subdivs.items()):
        out[div][sd] = {k: v for k, v in slots.items()}

print(f"  {len(out)} divisions")
total_sub = sum(len(v) for v in out.values())
print(f"  {total_sub} sub-divisions total")

with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, separators=(",",":"))

print(f"Written: {OUT_JSON}")

# Quick sanity check
sample_div = list(out.keys())[0]
sample_sd  = list(out[sample_div].keys())[0]
sample = out[sample_div][sample_sd]
print(f"\nSample: {sample_div} / {sample_sd}")
for slot in ("HOs","SOs","BOs"):
    lst = sample[slot]
    print(f"  {slot}: {len(lst)} offices, e.g. {lst[0] if lst else 'none'}")
