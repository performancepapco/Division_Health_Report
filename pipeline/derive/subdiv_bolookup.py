"""SUBDIV_DATA and BO_LOOKUP — a true cross-month cumulative view (not
month-keyed like everything else; these two tabs always show the full
cumulative across every month on record, joining POSB + PLI + RPLI +
Booking office-level data against the master roster). Ported from
build_subdiv_bolookup_june2026.py, but reads from this pipeline's own
stored data/dataset_<YYYY-MM>.json files instead of re-parsing raw
uploads, so it only ever depends on Phase 1's already-validated output —
never on raw files still being present on disk.

POSB and PLI/RPLI use different office-ID schemes. They do share one key,
though: the PLI/RPLI detail sheets' "Office Code" is the master data's
`pli_id`, which circle.office_geo_file carries per office_id. So insurance is
attributed by ID wherever that ID resolves to exactly one roster office
(~99.5% of rows), which is the only way a single office's real premium can be
shown on its own BO Lookup card.

Where it can't — a `pli_id` shared by several offices, a placeholder 0/blank,
or a feed code absent from the geo export — the legacy behaviour is the
fallback: join by (division, normalized office name) and split
policies/premium evenly (largest-remainder for the integer policy count)
across same-named offices. That keeps division and circle totals reconciling
exactly, at the cost of a per-office figure that is an average rather than the
office's own. pli_id_overrides.json corrects individual offices whose
master-data pli_id is wrong; see _load_pli_id_overrides below.
"""
import json
import re
from pathlib import Path
from collections import defaultdict

from pipeline.common import Roster, OfficeGeo, short_div, iso_to_label

BASE = Path(__file__).parent.parent.parent
DATA_DIR = BASE / "data"


def norm_name(s):
    if not s:
        return ""
    s = str(s).strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = s.replace(".", "").replace(",", "")
    s = re.sub(r"\bb\.?o\b", "bo", s)
    s = re.sub(r"\bs\.?o\b", "so", s)
    s = re.sub(r"\bh\.?o\b", "ho", s)
    return s.strip()


def infer_type(name):
    """New source files dropped the 'Office Type' column; approximate from
    name suffix — matches the legacy build_subdiv_bolookup_june2026.py.
    Phase 1's own posb.py deliberately leaves 'type' blank (matching the
    older build_posb_june2026.py it was verified against); this derived
    view needs a real value, so it's inferred here instead."""
    n = str(name or "").strip()
    if re.search(r"\bH\.?O\b\.?$", n, re.IGNORECASE):
        return "HPO"
    if re.search(r"\bS\.?O\b\.?$", n, re.IGNORECASE):
        return "SPO"
    return "BPO"


def _available_months() -> list[str]:
    return sorted(p.stem.removeprefix("dataset_") for p in DATA_DIR.glob("dataset_*.json"))


def _load_section(month_iso: str, section_name: str):
    p = DATA_DIR / f"dataset_{month_iso}.json"
    if not p.exists():
        return None
    dataset = json.loads(p.read_text(encoding="utf-8"))
    section = dataset["sections"].get(section_name)
    return section["standalone"] if section else None


def _build_posb_cumulative(months: list[str]):
    cum_offices = {}
    cum_schemes = defaultdict(lambda: defaultdict(lambda: {"o": 0, "c": 0, "n": 0}))
    real_divisions = set()
    for month in months:
        posb = _load_section(month, "posb")
        if not posb:
            continue
        for oid, rec in posb.get("offices", {}).items():
            real_divisions.add(rec["division"])
            if oid not in cum_offices:
                cum_offices[oid] = dict(rec, opened=0, closed=0, net=0)
            cum_offices[oid]["opened"] += rec["opened"]
            cum_offices[oid]["closed"] += rec["closed"]
            cum_offices[oid]["net"] += rec["net"]
            for k in ("name", "code", "division", "sub_division", "region"):
                if rec.get(k):
                    cum_offices[oid][k] = rec[k]
        for oid, sch in posb.get("schemes", {}).items():
            for scheme_name, v in sch.items():
                acc = cum_schemes[oid][scheme_name]
                acc["o"] += v["o"]; acc["c"] += v["c"]; acc["n"] += v["n"]
    return cum_offices, cum_schemes, real_divisions


def _load_pli_id_overrides() -> dict:
    """office_id -> corrected pli_id, from pli_id_overrides.json at the repo
    root (optional — an absent file just means no corrections). Only the
    "applied" block is honoured; "pending_upstream" records corrections whose
    ID doesn't exist in any feed yet, so applying them would attribute
    nothing. An override wins over the geo file's own pli_id."""
    p = BASE / "pli_id_overrides.json"
    if not p.exists():
        return {}
    blob = json.loads(p.read_text(encoding="utf-8"))
    return {str(k).strip(): str(v).strip()
            for k, v in (blob.get("applied") or {}).items() if v}


def _build_code_to_oid(roster: dict, office_geo: dict, overrides: dict):
    """pli_id -> office_id, but only where the ID identifies exactly ONE
    office in this roster. An ID claimed by several offices is deliberately
    left out rather than resolved arbitrarily — those fall through to the
    name-based split, which at least keeps totals right. Returns
    (code_to_oid, shared_ids, offices_without_id)."""
    by_code = defaultdict(list)
    without = 0
    for oid in roster:
        code = overrides.get(oid) or (office_geo.get(oid) or {}).get("pli_id")
        if code:
            by_code[str(code).strip()].append(oid)
        else:
            without += 1
    code_to_oid = {c: oids[0] for c, oids in by_code.items() if len(oids) == 1}
    shared = {c: oids for c, oids in by_code.items() if len(oids) > 1}
    return code_to_oid, shared, without


def _build_ins_cumulative(months: list[str], section_name: str):
    by_code = defaultdict(lambda: {"policies": 0, "premium": 0.0,
                                   "division": None, "name": None})
    by_name = defaultdict(lambda: {"policies": 0, "premium": 0.0})
    for month in months:
        section = _load_section(month, section_name)
        if not section:
            continue
        for r in section.get("offices", []):
            code = str(r.get("code") or "").strip()
            if code:
                # Accumulated per feed code, NOT per name: two same-named
                # offices in one division have distinct codes, and merging
                # them here is what used to force an even split.
                acc = by_code[code]
                acc["division"], acc["name"] = r["division"], r["name"]
            else:
                acc = by_name[(r["division"], norm_name(r["name"]))]
            acc["policies"] += r["policies"]
            acc["premium"] += r["premium"]
    return by_code, by_name


def _distribute_ins_to_offices(by_code: dict, by_name: dict,
                               name_to_oids: dict, code_to_oid: dict):
    """Attribute insurance to offices by pli_id first, falling back to the
    even name-split for anything that can't be resolved by ID. Returns
    (per_office, unmatched, stats) — `unmatched` keeps its legacy
    (division, normalized name) key shape, since callers roll those into
    "(Unmapped)" sub-divisions."""
    per_office = defaultdict(lambda: {"policies": 0, "premium": 0.0})
    unmatched = []
    fallback = defaultdict(lambda: {"policies": 0, "premium": 0.0})
    stats = {"by_id": 0, "by_name": 0, "id_unresolved": 0}

    for code, v in by_code.items():
        oid = code_to_oid.get(code)
        if oid:
            per_office[oid]["policies"] += v["policies"]
            per_office[oid]["premium"] += v["premium"]
            stats["by_id"] += 1
        else:
            stats["id_unresolved"] += 1
            acc = fallback[(v["division"], norm_name(v["name"]))]
            acc["policies"] += v["policies"]
            acc["premium"] += v["premium"]

    for key, v in by_name.items():
        acc = fallback[key]
        acc["policies"] += v["policies"]
        acc["premium"] += v["premium"]

    for key, v in fallback.items():
        oids = name_to_oids.get(key, [])
        if not oids:
            if v["policies"] or v["premium"]:
                unmatched.append((key, v))
            continue
        stats["by_name"] += len(oids)
        n = len(oids)
        base_pol, rem = divmod(v["policies"], n)
        for i, oid in enumerate(oids):
            per_office[oid]["policies"] += base_pol + (1 if i < rem else 0)
            per_office[oid]["premium"] += v["premium"] / n
    return per_office, unmatched, stats


def _load_posb_silent_snapshot(months: list[str]) -> dict:
    """posb_silent is a persistent snapshot (see pipeline/sections/
    posb_silent.py), not per-month activity to sum like POSB/PLI/booking
    above — so this just needs the latest month's already-merged
    cumulative rows, keyed by BO Code/SOL ID (falling back to a synthetic
    OID_<office_id> key for rows with no code)."""
    for month in reversed(months):
        section = _load_dataset_sections(month).get("posb_silent")
        if section and section.get("cumulative"):
            return section["cumulative"].get("rows", {})
    return {}


def _load_dataset_sections(month_iso: str) -> dict:
    p = DATA_DIR / f"dataset_{month_iso}.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8")).get("sections", {})


def _zero_booking_cum():
    return {"articles": 0, "amount": 0.0, "postage": 0.0, "vas": 0.0, "tax": 0.0,
            "fm_charges": 0.0, "ps_charges": 0.0, "ss_charges": 0.0}


def _read_booking_cumulative(months: list[str]):
    cum = defaultdict(lambda: defaultdict(_zero_booking_cum))
    for month in months:
        booking = _load_section(month, "booking")
        if not booking:
            continue
        for oid, rec in booking.get("by_office", {}).items():
            for pname, v in rec.get("by_prod", {}).items():
                acc = cum[oid][pname]
                acc["articles"] += v["articles"]
                acc["amount"] += v["business"]
                acc["postage"] += v.get("postage", 0)
                acc["vas"] += v.get("vas", 0)
                acc["tax"] += v.get("tax", 0)
                acc["fm_charges"] += v.get("fm_charges", 0)
                acc["ps_charges"] += v.get("ps_charges", 0)
                acc["ss_charges"] += v.get("ss_charges", 0)
    return cum


def _latest_dataset_field(months: list[str], section_name: str, field: str) -> str | None:
    """Max value of `field` across every month's stored section (booking's
    latest_booking_date, posb's as_of) — lets BO Lookup show a real as-of
    date instead of a fixed quarter label once a section is being
    re-uploaded daily as a month-to-date file rather than once at
    month-end."""
    latest = None
    for month in months:
        section = _load_section(month, section_name)
        if not section:
            continue
        v = section.get(field)
        if v and (latest is None or v > latest):
            latest = v
    return latest


def build(cfg: dict, months: list[str] | None = None,
          activity_months: list[str] | None = None,
          silent_months: list[str] | None = None) -> dict:
    """`months` scopes SUBDIV_DATA's real-divisions/roster resolution and is
    the default for the other two. `activity_months` scopes which months'
    POSB/PLI/RPLI/Booking activity gets summed into BO_LOOKUP (pass a single
    month here to get a non-cumulative slice — see build_by_month below).
    `silent_months` scopes the Silent Accounts snapshot lookup, which always
    wants the latest snapshot across every month on record regardless of
    activity_months, since it isn't month-summable activity."""
    months = months or _available_months()
    activity_months = activity_months or months
    silent_months = silent_months or months
    print(f"  Months on record: {months}")

    print("  Building POSB cumulative (office + scheme-wise)...")
    posb_offices, posb_schemes, real_divisions = _build_posb_cumulative(activity_months)
    print(f"    {len(posb_offices):,} offices with POSB activity, {len(real_divisions)} divisions")

    print("  Loading master office roster...")
    roster = Roster.offices_in_divisions(cfg, real_divisions)
    print(f"    {len(roster):,} real counter offices (BPO/SPO/HPO) in master roster")

    print("  Loading office location reference (pincode/lat-long/district/constituency)...")
    office_geo = OfficeGeo.load(cfg)
    print(f"    {len(office_geo):,} offices with location data")

    name_to_oids = defaultdict(list)
    for oid, rec in roster.items():
        name_to_oids[(rec["division"], norm_name(rec["name"]))].append(oid)

    overrides = _load_pli_id_overrides()
    code_to_oid, shared_ids, no_id = _build_code_to_oid(roster, office_geo, overrides)
    bits = [f"{len(code_to_oid):,} pli_id -> office_id mappings"]
    if overrides:
        bits.append(f"{len(overrides)} corrected via pli_id_overrides.json")
    if shared_ids:
        bits.append(f"{len(shared_ids)} pli_id(s) claimed by >1 office")
    if no_id:
        bits.append(f"{no_id} office(s) with no pli_id")
    print("    " + "; ".join(bits))

    print("  Building PLI cumulative...")
    pli_code, pli_name = _build_ins_cumulative(activity_months, "pli")
    pli_by_office, pli_unmatched, pli_stats = _distribute_ins_to_offices(
        pli_code, pli_name, name_to_oids, code_to_oid)
    print("  Building RPLI cumulative...")
    rpli_code, rpli_name = _build_ins_cumulative(activity_months, "rpli")
    rpli_by_office, rpli_unmatched, rpli_stats = _distribute_ins_to_offices(
        rpli_code, rpli_name, name_to_oids, code_to_oid)
    for label, st in (("PLI", pli_stats), ("RPLI", rpli_stats)):
        print(f"    {label}: {st['by_id']:,} attributed by pli_id, "
              f"{st['by_name']:,} by name-split "
              f"({st['id_unresolved']} feed code(s) unresolved)")
    if pli_unmatched or rpli_unmatched:
        print(f"    NOTE: {len(pli_unmatched)} PLI / {len(rpli_unmatched)} RPLI office names have no "
              f"match in the master roster at all (added as (Unmapped) entries)")

    print("  Building booking cumulative...")
    booking_cum = _read_booking_cumulative(activity_months)
    booking_as_of = _latest_dataset_field(activity_months, "booking", "latest_booking_date")
    posb_as_of = _latest_dataset_field(activity_months, "posb", "as_of")

    by_div = defaultdict(lambda: defaultdict(lambda: {
        "region": "", "offices": 0,
        "posb": {"opened": 0, "closed": 0, "net": 0},
        "pli": {"offices_procured": 0, "policies": 0, "premium": 0, "non_procurers": 0},
        "rpli": {"offices_procured": 0, "policies": 0, "premium": 0, "non_procurers": 0},
        "bos": [],
    }))
    bo_lookup = {}

    def add_office(oid, name, otype, code, div_s, sd, region, posb_rec, pli_v, rpli_v):
        opened, closed, net = (posb_rec["opened"], posb_rec["closed"], posb_rec["net"]) if posb_rec else (0, 0, 0)
        bo_rec = {
            "id": oid, "code": code, "name": name, "type": otype,
            "posb_opened": opened, "posb_closed": closed, "posb_net": net,
            "pli_policies": pli_v["policies"], "pli_premium": pli_v["premium"],
            "rpli_policies": rpli_v["policies"], "rpli_premium": rpli_v["premium"],
        }
        s = by_div[div_s][sd]
        s["region"] = region
        s["offices"] += 1
        s["posb"]["opened"] += opened
        s["posb"]["closed"] += closed
        s["posb"]["net"] += net
        s["bos"].append(bo_rec)

        bk = booking_cum.get(oid, {})
        prods = []
        tot_a, tot_amt = 0, 0.0
        tot_postage = tot_vas = tot_tax = tot_fm = tot_ps = tot_ss = 0.0
        for pname, v in sorted(bk.items(), key=lambda kv: (-kv[1]["amount"], kv[0])):
            if v["articles"] == 0 and v["amount"] == 0:
                continue
            prods.append({
                "n": pname, "a": v["articles"], "v": round(v["amount"], 2),
                "postage": round(v["postage"], 2), "vas": round(v["vas"], 2), "tax": round(v["tax"], 2),
                "fm": round(v["fm_charges"], 2), "ps": round(v["ps_charges"], 2), "ss": round(v["ss_charges"], 2),
            })
            tot_a += v["articles"]; tot_amt += v["amount"]
            tot_postage += v["postage"]; tot_vas += v["vas"]; tot_tax += v["tax"]
            tot_fm += v["fm_charges"]; tot_ps += v["ps_charges"]; tot_ss += v["ss_charges"]

        geo = office_geo.get(oid, {})
        bo_lookup[oid] = {
            "id": oid, "code": code, "name": name, "type": otype,
            "sub_division": sd, "division": div_s, "region": region,
            "pincode": geo.get("pincode"),
            "district": geo.get("district"), "constituency": geo.get("constituency"),
            "tribal": geo.get("tribal", False),
            "lat": geo.get("lat"), "lon": geo.get("lon"),
            "posb": {"opened": opened, "closed": closed, "net": net, "as_of": posb_as_of},
            "posb_schemes": posb_schemes.get(oid, {}),
            "pli": {"policies": pli_v["policies"], "premium": pli_v["premium"]},
            "rpli": {"policies": rpli_v["policies"], "premium": rpli_v["premium"]},
            "booking": {
                "as_of": booking_as_of,
                "total_articles": tot_a, "total_amount": round(tot_amt, 2),
                "total_postage": round(tot_postage, 2), "total_vas": round(tot_vas, 2),
                "total_tax": round(tot_tax, 2), "total_fm": round(tot_fm, 2),
                "total_ps": round(tot_ps, 2), "total_ss": round(tot_ss, 2),
                "products": prods,
            },
            "nil_posb": posb_rec is None,
        }

    zero_ins = {"policies": 0, "premium": 0.0}
    for oid, rec in roster.items():
        posb_rec = posb_offices.get(oid)
        name = posb_rec["name"] if posb_rec else rec["name"]
        otype = infer_type(posb_rec["name"]) if posb_rec else rec["type"]
        code = posb_rec["code"] if posb_rec else ""
        sd = posb_rec["sub_division"] if posb_rec else rec["sub_division"]
        region = posb_rec["region"] if posb_rec else rec["region"]
        add_office(oid, name, otype, code, rec["division"], sd, region, posb_rec,
                   pli_by_office.get(oid, zero_ins), rpli_by_office.get(oid, zero_ins))

    extra = 0
    for oid, rec in posb_offices.items():
        if oid in roster:
            continue
        extra += 1
        add_office(oid, rec["name"], infer_type(rec["name"]), rec["code"], rec["division"], rec["sub_division"],
                   rec["region"], rec, pli_by_office.get(oid, zero_ins), rpli_by_office.get(oid, zero_ins))
    if extra:
        print(f"    NOTE: {extra} offices had POSB activity but aren't in the filtered master roster "
              f"(kept anyway, e.g. hierarchy drift)")

    print("  Joining POSB Silent Accounts snapshot...")
    silent_rows = _load_posb_silent_snapshot(silent_months)
    code_to_oid = {str(r["code"]): oid for oid, r in bo_lookup.items() if r.get("code")}
    silent_matched, silent_unmatched = 0, []
    for key, srec in silent_rows.items():
        code_val = None if key.startswith("OID_") else key
        oid = code_to_oid.get(code_val) if code_val else None
        if oid is None and srec.get("office_id") in bo_lookup:
            oid = srec["office_id"]
        if oid is None:
            silent_unmatched.append(key)
            continue
        bo_lookup[oid]["posb_silent"] = {
            "as_of": srec["as_of"],
            "silent_accounts": srec["silent_accounts"],
            "sbbas_silent": srec["sbbas_silent"],
            "sbgen_silent": srec["sbgen_silent"],
            "live_accounts": srec["live_accounts"],
            "live_sb": srec["live_sb"],
            "silent_ratio_pct": srec["silent_ratio_pct"],
            "fy_revival_approx": srec["fy_revival_approx"],
            "revival_basis": srec["revival_basis"],
            "fy_months": srec["fy_months"],
        }
        silent_matched += 1
    if silent_rows:
        print(f"    {silent_matched:,} offices matched"
              + (f", {len(silent_unmatched)} upload rows had no matching office in BO_LOOKUP (logged, not created)"
                 if silent_unmatched else ""))

    for key, v in pli_unmatched:
        div_s, _ = key
        sd = "(Unmapped)"
        by_div[div_s][sd]["region"] = by_div[div_s][sd]["region"] or ""
        by_div[div_s][sd]["pli"]["policies"] += v["policies"]
        by_div[div_s][sd]["pli"]["premium"] += v["premium"]
    for key, v in rpli_unmatched:
        div_s, _ = key
        sd = "(Unmapped)"
        by_div[div_s][sd]["region"] = by_div[div_s][sd]["region"] or ""
        by_div[div_s][sd]["rpli"]["policies"] += v["policies"]
        by_div[div_s][sd]["rpli"]["premium"] += v["premium"]

    for div, subs in by_div.items():
        for sd, s in subs.items():
            s["pli"]["offices_procured"] = sum(1 for b in s["bos"] if b["pli_policies"] > 0)
            s["pli"]["policies"] = sum(b["pli_policies"] for b in s["bos"]) + s["pli"]["policies"]
            s["pli"]["premium"] = sum(b["pli_premium"] for b in s["bos"]) + s["pli"]["premium"]
            s["pli"]["non_procurers"] = sum(1 for b in s["bos"] if b["pli_policies"] == 0)
            s["rpli"]["offices_procured"] = sum(1 for b in s["bos"] if b["rpli_policies"] > 0)
            s["rpli"]["policies"] = sum(b["rpli_policies"] for b in s["bos"]) + s["rpli"]["policies"]
            s["rpli"]["premium"] = sum(b["rpli_premium"] for b in s["bos"]) + s["rpli"]["premium"]
            s["rpli"]["non_procurers"] = sum(1 for b in s["bos"] if b["rpli_policies"] == 0)

    subdiv_out = {div: {"subdivs": {sd: dict(s) for sd, s in subs.items()}} for div, subs in by_div.items()}

    search_idx = []
    for oid, r in bo_lookup.items():
        name_n = norm_name(r["name"])
        search_idx.append({
            "id": oid, "n": r["name"], "c": r["code"], "t": r["type"],
            "d": r["division"], "r": r["region"], "sd": r["sub_division"],
            "k": f"{name_n} {(r['code'] or '').lower()} {oid}".strip(),
        })

    total_offices = sum(s["offices"] for d in by_div.values() for s in d.values())
    print(f"  SUBDIV_DATA: {len(by_div)} divisions, {sum(len(d) for d in by_div.values())} subdivisions, {total_offices} offices")
    print(f"  BO_LOOKUP: {len(bo_lookup):,} offices")

    return {"subdiv_data": subdiv_out, "bo_lookup": {"lookup": bo_lookup, "index": search_idx}}


def build_by_month(cfg: dict, months: list[str] | None = None) -> dict:
    """Single-month BO_LOOKUP slices, keyed by month label, so the dashboard's
    Period selector can drive office-level BO Lookup figures the same way it
    already drives POSB_BY_MONTH/PLI_POLICIES/BOOKING_BY_MONTH — pick a
    From/To range and sum the relevant slices client-side. Each slice's
    Silent Accounts snapshot still comes from the latest month on record
    overall (see build()'s silent_months), since that data isn't
    month-summable activity."""
    all_months = months or _available_months()
    out = {}
    for month in all_months:
        print(f"  Building BO_LOOKUP slice for {month}...")
        result = build(cfg, months=[month], activity_months=[month], silent_months=all_months)
        out[iso_to_label(month)] = result["bo_lookup"]["lookup"]
    return out
