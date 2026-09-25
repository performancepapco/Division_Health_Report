"""data/booking_offices.json — compact per-office monthly booking records so
the dashboard can rebuild the Booking tab for any From/To range
client-side.

BOOKING_BY_MONTH (assemble.py) only carries single months plus the full
Cumulative, and its top-25 / top-by-product lists and distinct-office counts
can't be combined across months. This file holds exactly what
booking._build_scope() consumes per office, so index.html's port of it
(computeBookingRange) reproduces booking.build_cumulative_pack() for any
contiguous range. The per-scope daily series isn't included — each month's
own slice already has it exactly, and months don't share days.

Lazily fetched by the Booking tab only when a partial range is selected.

Shape:
  months:   ["Apr-26", ...]
  products: [product name, ...]                       (index table)
  hier:     {"circle": n, "div": {div: n}, "region": {reg: n}}
                                                      (total_offices_in_hier)
  offices:  [[oid, [name per month or null], div, region], ...]
  m:        per office, per month: null (no booking record that month) or
            [articles, business, walk_in, bulk_bnpl, postal_service,
             commercial, other, [prod_idx, articles, business, ...]]
"""
import json
from pathlib import Path
from collections import defaultdict

from pipeline.common import iso_to_label
from pipeline.sections.booking import load_hierarchy

BASE = Path(__file__).parent.parent.parent
DATA_DIR = BASE / "data"
MIX_KEYS = ("walk_in", "bulk_bnpl", "postal_service", "commercial", "other")


def _load_booking(month_iso: str) -> dict:
    p = DATA_DIR / f"dataset_{month_iso}.json"
    if not p.exists():
        return {}
    section = json.loads(p.read_text(encoding="utf-8"))["sections"].get("booking")
    return section["standalone"] if section else {}


def build(months: list[str]) -> dict:
    hierarchy = load_hierarchy()
    hier = {"circle": len(hierarchy), "div": defaultdict(int), "region": defaultdict(int)}
    for info in hierarchy.values():
        hier["div"][info["division"]] += 1
        hier["region"][info["region"]] += 1

    packs = [_load_booking(m) for m in months]
    prod_idx = {}
    office_ids = []
    seen = set()
    for pack in packs:
        for oid in pack.get("by_office", {}):
            if oid not in seen:
                seen.add(oid)
                office_ids.append(oid)
    office_ids.sort()

    offices, recs = [], []
    for oid in office_ids:
        info = hierarchy.get(oid) or {}
        names, per_month = [], []
        for pack in packs:
            rec = pack.get("by_office", {}).get(oid)
            if rec is None:
                names.append(None)
                per_month.append(None)
                continue
            names.append(rec["name"])
            mix = pack.get("mix_by_office", {}).get(oid, {})
            prods = []
            for pname, pv in rec["by_prod"].items():
                if pname not in prod_idx:
                    prod_idx[pname] = len(prod_idx)
                prods += [prod_idx[pname], pv["articles"], pv["business"]]
            per_month.append([rec["articles"], rec["business"]]
                             + [mix.get(k, 0) for k in MIX_KEYS] + [prods])
        # Names rarely change month to month; collapse to one string when
        # they don't, to keep the file small.
        distinct = {n for n in names if n is not None}
        offices.append([oid, names[next(i for i, n in enumerate(names) if n is not None)]
                        if len(distinct) == 1 else names,
                        info.get("division", ""), info.get("region", "")])
        recs.append(per_month)

    return {
        "months": [iso_to_label(m) for m in months],
        "products": sorted(prod_idx, key=prod_idx.get),
        "hier": {"circle": hier["circle"], "div": dict(hier["div"]), "region": dict(hier["region"])},
        "offices": offices,
        "m": recs,
    }
