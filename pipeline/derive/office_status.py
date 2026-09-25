"""OFFICE_STATUS_BY_MONTH — NIL & low-booking office buckets (HO/SO/BO/Other)
per division/region/circle, month-keyed plus a true Cumulative sum, matching
the Booking tab's own "View month" switcher. Ported from
build_office_status_by_month.py.

Bucket rule (reverse-engineered there, not documented anywhere upstream):
HO=HPO, SO=SPO, BO=BPO, Other=everything except HPO/SPO/BPO/SDO (SDO = an
admin unit, excluded to match the tab's own "Admin offices excluded" note).
NIL = 0 articles in the window; Low = 1-5 articles.

Reads Booking's own already-extracted by_office totals from
data/dataset_<month>.json rather than raw CSVs — same reuse principle as
subdiv_bolookup.py.
"""
import json
from pathlib import Path
from collections import defaultdict

from pipeline.sections.booking import load_hierarchy
from pipeline.common import iso_to_label

BASE = Path(__file__).parent.parent.parent
DATA_DIR = BASE / "data"

TYPES = [
    ("HO", lambda t: t == "HPO"),
    ("SO", lambda t: t == "SPO"),
    ("BO", lambda t: t == "BPO"),
    ("Other", lambda t: t not in ("HPO", "SPO", "BPO", "SDO")),
]
LIST_CAP = 100


def _load_booking_by_office(month_iso: str) -> dict:
    p = DATA_DIR / f"dataset_{month_iso}.json"
    if not p.exists():
        return {}
    dataset = json.loads(p.read_text(encoding="utf-8"))
    section = dataset["sections"].get("booking")
    return section["standalone"].get("by_office", {}) if section else {}


def _build_bucket(offices, by_off):
    total = len(offices)
    nil_list, low_list = [], []
    nil_n = low_n = 0
    low_biz = 0.0
    active_total_biz = 0.0
    for oid, name in offices:
        rec = by_off.get(oid)
        arts = rec["articles"] if rec else 0
        biz = rec["business"] if rec else 0.0
        if arts == 0:
            nil_n += 1
            if len(nil_list) < LIST_CAP:
                nil_list.append({"id": oid, "name": name})
        elif arts <= 5:
            low_n += 1
            low_biz += biz
            if len(low_list) < LIST_CAP:
                low_list.append({"id": oid, "name": name, "arts": arts, "biz": round(biz, 2)})
        else:
            active_total_biz += biz
    return {
        "total": total, "nil": nil_n, "low": low_n,
        "low_biz": round(low_biz, 2), "active_total_biz": round(active_total_biz, 2),
        "nilList": nil_list, "lowList": low_list,
    }


def _build_month_status(by_off, hierarchy_by_bucket):
    by_div = defaultdict(dict)
    by_reg = defaultdict(dict)
    circle = {}
    for bucket, offices_by_div, offices_by_reg, all_offices, _meta in hierarchy_by_bucket:
        for div, offs in offices_by_div.items():
            by_div[div][bucket] = _build_bucket(offs, by_off)
        for reg, offs in offices_by_reg.items():
            by_reg[reg][bucket] = _build_bucket(offs, by_off)
        circle[bucket] = _build_bucket(all_offices, by_off)
    return {"circle": circle, "byDiv": dict(by_div), "byReg": dict(by_reg)}


def build(months: list[str]) -> dict:
    hierarchy_by_bucket = _hierarchy_by_bucket()

    out = {}
    cum_off = defaultdict(lambda: {"articles": 0, "business": 0.0})
    for month in months:
        by_off = _load_booking_by_office(month)
        label = iso_to_label(month)
        out[label] = _build_month_status(by_off, hierarchy_by_bucket)
        for oid, rec in by_off.items():
            cum_off[oid]["articles"] += rec["articles"]
            cum_off[oid]["business"] += rec["business"]

    out["Cumulative"] = _build_month_status(dict(cum_off), hierarchy_by_bucket)
    return out


def build_offices(months: list[str]) -> dict:
    """Per-office monthly articles/business, compact, so the dashboard can
    rebuild the NIL & low-booking buckets for any From/To range client-side
    (build() only covers single months + the full Cumulative, and its office
    lists are capped at LIST_CAP, so partial ranges can't be derived from
    it). Written to its own lazily-fetched file (data/office_status_offices.json)
    rather than latest.json, since it's only needed for a partial range.

    Offices are listed in the same order build() walks them (bucket by
    bucket, hierarchy order within), so the client's capped lists match
    build()'s exactly. Only NIL/Low status matters, so per-month articles
    are capped at LOW_MAX + 1 (any month above 5 already rules an office
    out of both buckets for every range containing it) and business is
    kept only for months with 1-5 articles."""
    low_max = 5
    labels = [iso_to_label(m) for m in months]
    by_month = [_load_booking_by_office(m) for m in months]
    offices, arts, biz = [], [], []
    for b_idx, (_bucket, _by_div, _by_reg, _offs, all_meta) in enumerate(_hierarchy_by_bucket()):
        for oid, name, div, region in all_meta:
            offices.append([oid, name, b_idx, div, region])
            a_row, b_row = [], []
            for by_off in by_month:
                rec = by_off.get(oid)
                a = rec["articles"] if rec else 0
                a_row.append(min(a, low_max + 1))
                b_row.append(round(rec["business"], 2) if rec and 0 < a <= low_max else 0)
            arts.append(a_row)
            biz.append(b_row)
    return {"months": labels, "buckets": [t[0] for t in TYPES], "list_cap": LIST_CAP,
            "low_max": low_max, "offices": offices, "arts": arts, "biz": biz}


def _hierarchy_by_bucket():
    """[(bucket, offices_by_div, offices_by_reg, all_offices)] — the per-bucket
    office rosters build() and build_offices() both walk. Office entries are
    (oid, name); all_meta carries the same offices as (oid, name, division,
    region) for build_offices()."""
    hier = load_hierarchy()

    hierarchy_by_bucket = []
    for bucket, matches in TYPES:
        offices_by_div = defaultdict(list)
        offices_by_reg = defaultdict(list)
        all_offices, all_meta = [], []
        for oid, info in hier.items():
            if not matches(info["type"]):
                continue
            if not info["division"]:
                continue
            name = info["name"]
            offices_by_div[info["division"]].append((oid, name))
            if info["region"]:
                offices_by_reg[info["region"]].append((oid, name))
            all_offices.append((oid, name))
            all_meta.append((oid, name, info["division"], info["region"] or ""))
        hierarchy_by_bucket.append((bucket, offices_by_div, offices_by_reg, all_offices, all_meta))
    return hierarchy_by_bucket
