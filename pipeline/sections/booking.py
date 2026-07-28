"""Booking — the one section that genuinely needs two files at once
(Product-wise + Book-type-wise), unlike every other section. The Form has
two separate upload entries (booking_productwise / booking_booktypewise,
each independently validated against its own header spec when it arrives),
but a meaningful booking "pack" (daily trend, top-25 offices, product mix,
customer mix) can only be built once both files for a month are present —
see build_dataset.py's special-cased --section booking path.

If the book-type-wise file is missing, extraction still proceeds (matching
the legacy script's tolerance) with an all-zero customer_mix; a later run
with both files present overwrites it with the fuller data.

Hierarchy source is office_hierarchy.json, not the Hierarchy_data.xlsx-based
Roster used by POSB/PLI/RPLI — checked deliberately: office_hierarchy.json
covers ~10,952 offices across every office type code (RMS/admin units
included), while the Roster used elsewhere is filtered to real counter
offices (BPO/SPO/HPO) only. Booking activity legitimately happens at
non-counter offices too, so swapping to the filtered roster would silently
drop ~300 offices' booking data from division/region rollups.

No cross-month merge happens here (cumulative_mode: none for the pipeline's
purposes) — a real "Cumulative" scope (top-25s recomputed across the full
range, not just summed) is assembled from multiple months' extracted packs
in Phase 2, the same way the legacy patch_booking_months.py's build_month()
was called once per month plus once more for the merged range.
"""
import csv
import json
import re
from pathlib import Path
from collections import defaultdict

from pipeline.validate import validate_csv, ValidationError
from pipeline.common import short_div, short_region

BASE = Path(__file__).parent.parent.parent
HIERARCHY_FILE = BASE / "office_hierarchy.json"
CR = 10_000_000
L = 100_000


def load_hierarchy() -> dict:
    with open(HIERARCHY_FILE, encoding="utf-8") as f:
        h = json.load(f)
    out = {}
    for k, v in h.items():
        out[str(k)] = {
            "division": short_div(v.get("division", "")),
            "region":   short_region(v.get("region", "")),
            "name":     v.get("name", ""),
            "type":     v.get("type", ""),
        }
    return out


def validate_productwise(section_cfg: dict, path, month_iso: str) -> list[ValidationError]:
    errors = validate_csv("booking_productwise", "Booking Product-wise file", path,
                           section_cfg["csv_headers"])
    if errors:
        return errors
    # Month-in-file check: booking-date should fall within the declared month.
    bad = 0
    total = 0
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            date = (row.get("booking-date") or "")[:10]
            if not date:
                continue
            total += 1
            if not date.startswith(month_iso):
                bad += 1
    if total and bad / total > 0.05:  # tolerate a handful of stray boundary rows
        return [ValidationError("booking_productwise",
            f"Booking Product-wise file: {bad:,} of {total:,} rows have a booking-date "
            f"outside {month_iso} — please upload the file for the month you selected.")]
    return []


def validate_booktypewise(section_cfg: dict, path, month_iso: str) -> list[ValidationError]:
    # No reliable per-row date field in this file to cross-check against the
    # declared month (matches the legacy script, which never checked either).
    return validate_csv("booking_booktypewise", "Booking Book-type-wise file", path,
                         section_cfg["csv_headers"])


CHARGE_KEYS = ("postage", "vas", "tax", "fm_charges", "ps_charges", "ss_charges")


def _zero_by_prod():
    return {"articles": 0, "business": 0.0, "postage": 0.0, "vas": 0.0, "tax": 0.0,
            "fm_charges": 0.0, "ps_charges": 0.0, "ss_charges": 0.0}


def _read_productwise(path):
    by_off = defaultdict(lambda: {
        "name": None, "articles": 0, "business": 0.0,
        "products": set(),
        "daily": defaultdict(lambda: {"articles": 0, "business": 0.0}),
        "by_prod": defaultdict(_zero_by_prod),
    })
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            oid = (row.get("office-id") or "").strip()
            if not oid or oid == "-":
                continue
            oname = (row.get("office-name") or "").strip()
            date = (row.get("booking-date") or "")[:10]
            pname = (row.get("product-name") or "").strip()
            arts = int(row.get("article-count") or 0)
            amt = float(row.get("total_amount") or 0)
            postage = float(row.get("postage") or 0)
            vas = float(row.get("vas") or 0)
            tax = float(row.get("tax") or 0)
            fm = float(row.get("fm-charges") or 0)
            ps = float(row.get("ps-charges") or 0)
            ss = float(row.get("ss-charges") or 0)
            if not pname or not date:
                continue
            rec = by_off[oid]
            if rec["name"] is None:
                rec["name"] = oname
            rec["articles"] += arts
            rec["business"] += amt
            rec["products"].add(pname)
            rec["daily"][date]["articles"] += arts
            rec["daily"][date]["business"] += amt
            bp = rec["by_prod"][pname]
            bp["articles"] += arts
            bp["business"] += amt
            bp["postage"] += postage
            bp["vas"] += vas
            bp["tax"] += tax
            bp["fm_charges"] += fm
            bp["ps_charges"] += ps
            bp["ss_charges"] += ss
    return by_off


def _read_booktypewise(path):
    out = defaultdict(lambda: {"walk_in": 0, "bulk_bnpl": 0, "postal_service": 0,
                                "commercial": 0, "other": 0})
    if path is None:
        return out
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            oid = (row.get("Office ID") or "").strip()
            if not oid or oid == "-":
                continue
            wi = (int(row.get("Walk-in Customer") or 0) + int(row.get("Walk-in Non-Commercial") or 0)
                  + int(row.get("Walk-in Commercial") or 0) + int(row.get("Walk-in E-commerce") or 0))
            bb = (int(row.get("Registered Bulk") or 0) + int(row.get("Bulk Non-Commercial") or 0)
                  + int(row.get("Bulk Commercial") or 0) + int(row.get("Bulk E-commerce") or 0))
            ps = (int(row.get("On Postal Service") or 0) + int(row.get("Govt Service") or 0)
                  + int(row.get("Inter FPO") or 0))
            cm = int(row.get("Commercial") or 0) + int(row.get("E-commerce") or 0)
            other = (int(row.get("Non-Commercial") or 0) + int(row.get("Others") or 0)
                     + int(row.get("PIDPI") or 0) + int(row.get("Student Mail") or 0)
                     + int(row.get("BO Rebooking") or 0) + int(row.get("Free Active Service") or 0))
            r = out[oid]
            r["walk_in"] += wi; r["bulk_bnpl"] += bb; r["postal_service"] += ps
            r["commercial"] += cm; r["other"] += other
    return out


def _build_scope(label, scope_offices, by_off, mix_by_off, total_offices_in_hier):
    arts = 0; biz = 0.0
    prod_agg = defaultdict(lambda: {"articles": 0, "business": 0.0, "offices": set()})
    prod_office_agg = defaultdict(dict)
    daily_agg = defaultdict(lambda: {"articles": 0, "business": 0.0})
    mix = {"walk_in": 0, "bulk_bnpl": 0, "postal_service": 0, "commercial": 0, "other": 0}
    active = 0
    office_summaries = []

    for oid in scope_offices:
        rec = by_off.get(oid)
        if not rec:
            continue
        active += 1
        arts += rec["articles"]
        biz += rec["business"]
        for pname, pv in rec["by_prod"].items():
            prod_agg[pname]["articles"] += pv["articles"]
            prod_agg[pname]["business"] += pv["business"]
            prod_agg[pname]["offices"].add(oid)
            if pv["articles"] > 0 or pv["business"] > 0:
                prod_office_agg[pname][oid] = {
                    "name": rec["name"], "articles": pv["articles"], "business": pv["business"],
                }
        for d, dv in rec["daily"].items():
            daily_agg[d]["articles"] += dv["articles"]
            daily_agg[d]["business"] += dv["business"]
        m = mix_by_off.get(oid, {})
        for k in mix:
            mix[k] += m.get(k, 0)
        office_summaries.append({
            "id": oid, "name": rec["name"], "articles": rec["articles"],
            "business": rec["business"], "products": len(rec["products"]),
        })

    prod_list = []
    for pname, v in sorted(prod_agg.items(), key=lambda kv: (-kv[1]["business"], kv[0])):
        prod_list.append({
            "name": pname, "articles": v["articles"], "business": round(v["business"], 2),
            "offices": len(v["offices"]), "business_cr": round(v["business"] / CR, 4),
            "business_l": round(v["business"] / L, 4),
        })

    top_by_product = {}
    for pname, off_map in prod_office_agg.items():
        # Secondary sort key (office id) makes ties deterministic — without
        # it, which office wins a tied spot depends on dict/set iteration
        # order, which varies by Python's per-process hash randomization.
        ranked = sorted(off_map.items(), key=lambda kv: (-kv[1]["business"], kv[0]))[:25]
        top_by_product[pname] = [{
            "id": oid, "name": v["name"], "articles": v["articles"],
            "business": round(v["business"], 2), "business_l": round(v["business"] / L, 4),
            "avg_rs": round(v["business"] / v["articles"], 2) if v["articles"] > 0 else 0,
        } for oid, v in ranked]

    daily_list = [{
        "date": d, "articles": daily_agg[d]["articles"],
        "business_l": round(daily_agg[d]["business"] / L, 4),
    } for d in sorted(daily_agg.keys())]

    peak = max(daily_list, key=lambda x: x["articles"]) if daily_list else None
    trough = min(daily_list, key=lambda x: x["articles"]) if daily_list else None

    office_summaries.sort(key=lambda o: (-o["business"], o["id"]))
    top25 = [{
        "id": o["id"], "name": o["name"], "articles": o["articles"],
        "business": round(o["business"], 2), "products": o["products"],
        "business_l": round(o["business"] / L, 4),
        "avg_rs": round(o["business"] / o["articles"], 2) if o["articles"] > 0 else 0,
    } for o in office_summaries[:25]]

    days = len(daily_list)
    inactive = max(0, total_offices_in_hier - active)
    mix["total"] = arts

    return {
        "label": label,
        "totals": {
            "articles": arts, "business_cr": round(biz / CR, 4), "business_l": round(biz / L, 4),
            "active_offices": active, "total_offices_in_hier": total_offices_in_hier,
            "inactive_offices": inactive, "products": len(prod_list), "days": days,
            "avg_articles_per_day": round(arts / days, 4) if days > 0 else 0,
            "avg_rs_per_article": round(biz / arts, 4) if arts > 0 else 0,
        },
        "customer_mix": mix,
        "products": prod_list,
        "daily": daily_list,
        "top_offices": top25,
        "top_offices_by_product": top_by_product,
        "peak_day": {"date": peak["date"], "articles": peak["articles"], "business_l": peak["business_l"]} if peak else None,
        "trough_day": {"date": trough["date"], "articles": trough["articles"], "business_l": trough["business_l"]} if trough else None,
    }


def _build_month(label, by_off, mix_by_off, hierarchy):
    div_offices = defaultdict(set)
    reg_offices = defaultdict(set)
    all_offices = set(by_off.keys())
    for oid in by_off.keys():
        info = hierarchy.get(oid)
        if not info:
            continue
        div_offices[info["division"]].add(oid)
        reg_offices[info["region"]].add(oid)

    div_hier_count = defaultdict(int)
    reg_hier_count = defaultdict(int)
    for oid, info in hierarchy.items():
        div_hier_count[info["division"]] += 1
        reg_hier_count[info["region"]] += 1

    by_div_out = {div: _build_scope(div, offs, by_off, mix_by_off, div_hier_count[div])
                  for div, offs in div_offices.items() if div}
    by_reg_out = {reg: _build_scope(reg, offs, by_off, mix_by_off, reg_hier_count[reg])
                  for reg, offs in reg_offices.items() if reg}
    circle = _build_scope("AP Circle", all_offices, by_off, mix_by_off, len(hierarchy))

    return {"label": label, "circle": circle, "by_region": by_reg_out, "by_div": by_div_out}


def _serializable_by_office(by_off: dict) -> dict:
    """Raw per-office product + daily totals (drops only the 'products' set
    _build_scope needs internally) — this is what
    pipeline/derive/subdiv_bolookup.py and assemble.py's cross-month
    "Cumulative" merge consume instead of re-parsing the raw CSV, so
    derived views only ever depend on this pipeline's own stored output,
    never on raw uploads still being present on disk. 'daily' must be kept
    (not just totals) so a true multi-month merge can recompute daily
    trends/peak-day across the full range, matching what the legacy
    merge_offices() did with in-memory data."""
    out = {}
    for oid, rec in by_off.items():
        out[oid] = {
            "name": rec["name"],
            "articles": rec["articles"],
            "business": round(rec["business"], 2),
            "daily": {d: {"articles": v["articles"], "business": round(v["business"], 2)}
                      for d, v in rec["daily"].items()},
            "by_prod": {p: {"articles": v["articles"], "business": round(v["business"], 2),
                             **{k: round(v[k], 2) for k in CHARGE_KEYS}}
                        for p, v in rec["by_prod"].items()},
        }
    return out


def extract(productwise_path, booktypewise_path, month_iso: str) -> dict:
    hierarchy = load_hierarchy()
    by_off = _read_productwise(productwise_path)
    mix = _read_booktypewise(booktypewise_path)
    pack = _build_month(month_iso, by_off, mix, hierarchy)
    pack["by_office"] = _serializable_by_office(by_off)
    # Per-office customer mix, kept alongside (not merged into by_office) so
    # assemble.py's cross-month "Cumulative" rebuild has everything
    # _build_month() needs without re-parsing the raw book-type-wise CSV.
    pack["mix_by_office"] = {oid: dict(v) for oid, v in mix.items()}
    return pack


def merge_cumulative(new_slice: dict, previous_cumulative: dict | None) -> dict:
    return new_slice


def row_count(data: dict) -> int:
    return data.get("circle", {}).get("totals", {}).get("articles", 0) if data else 0


def _deserialize_by_office(stored: dict) -> dict:
    """Inverse of _serializable_by_office — rebuilds the defaultdict/set
    working shape _build_scope() expects from one month's stored record."""
    out = {}
    for oid, rec in stored.items():
        out[oid] = {
            "name": rec["name"],
            "articles": rec["articles"],
            "business": rec["business"],
            "products": set(rec["by_prod"].keys()),
            "daily": defaultdict(lambda: {"articles": 0, "business": 0.0}, rec["daily"]),
            "by_prod": defaultdict(_zero_by_prod, rec["by_prod"]),
        }
    return out


def build_cumulative_pack(monthly_packs: list[dict], month_label: str = "Cumulative") -> dict:
    """Re-derives a true cross-month scope (top-25s, daily trend, product
    mix recomputed over the full range — not just unioned per-month lists)
    from each month's stored {by_office, mix_by_office}, the same
    capability the legacy merge_offices()+build_month("Cumulative", ...)
    had, just fed from this pipeline's stored JSON instead of in-memory
    state from a single script run covering all months at once."""
    hierarchy = load_hierarchy()
    merged_off = {}
    merged_mix = defaultdict(lambda: {"walk_in": 0, "bulk_bnpl": 0, "postal_service": 0,
                                       "commercial": 0, "other": 0})
    for pack in monthly_packs:
        month_off = _deserialize_by_office(pack.get("by_office", {}))
        for oid, rec in month_off.items():
            if oid not in merged_off:
                merged_off[oid] = {
                    "name": rec["name"], "articles": 0, "business": 0.0,
                    "products": set(),
                    "daily": defaultdict(lambda: {"articles": 0, "business": 0.0}),
                    "by_prod": defaultdict(lambda: {"articles": 0, "business": 0.0}),
                }
            merged_off[oid] = merge_offices_working(merged_off[oid], rec)
        for oid, m in pack.get("mix_by_office", {}).items():
            for k in ("walk_in", "bulk_bnpl", "postal_service", "commercial", "other"):
                merged_mix[oid][k] += m.get(k, 0)

    return _build_month(month_label, merged_off, merged_mix, hierarchy)


def merge_offices_working(rec_a: dict, rec_b: dict) -> dict:
    """Merge two internal (defaultdict-shaped) by-office records."""
    out = {
        "name": rec_a.get("name") or rec_b.get("name"),
        "articles": rec_a["articles"] + rec_b["articles"],
        "business": rec_a["business"] + rec_b["business"],
        "products": rec_a["products"] | rec_b["products"],
        "daily": defaultdict(lambda: {"articles": 0, "business": 0.0}),
        "by_prod": defaultdict(_zero_by_prod),
    }
    for d, v in rec_a["daily"].items():
        out["daily"][d]["articles"] += v["articles"]; out["daily"][d]["business"] += v["business"]
    for d, v in rec_b["daily"].items():
        out["daily"][d]["articles"] += v["articles"]; out["daily"][d]["business"] += v["business"]
    for p, v in rec_a["by_prod"].items():
        for k in ("articles", "business") + CHARGE_KEYS:
            out["by_prod"][p][k] += v[k]
    for p, v in rec_b["by_prod"].items():
        for k in ("articles", "business") + CHARGE_KEYS:
            out["by_prod"][p][k] += v[k]
    return out
