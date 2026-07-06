#!/usr/bin/env python3
"""
build_booking_june2026.py
───────────────────────────
Extends the Booking-tab month-switcher data with June 2026, reusing the
read/aggregate helpers from patch_booking_months.py. Produces the full
BOOKING_BY_MONTH dict (Apr-26, May-26, Jun-26, Cumulative = Apr+May+Jun)
and writes it to _booking_by_month_june.json for patch_june2026.py to inject.

Run:  python build_booking_june2026.py
"""
import json
from pathlib import Path
from collections import defaultdict

from patch_booking_months import (
    load_hierarchy, read_productwise, read_booktypewise, build_month, merge_offices,
    APR_PROD, APR_BOOK, MAY_PROD, MAY_BOOK,
)

BASE = Path(__file__).parent
JUN_PROD = BASE / "uploads" / "june_2026" / "Booking_Productwise_Report.csv"
JUN_BOOK = BASE / "uploads" / "june_2026" / "Booking_BookTypewise_Datewise_Report.csv"


def empty_rec():
    return {"name": None, "articles": 0, "business": 0.0,
             "products": set(),
             "daily": defaultdict(lambda: {"articles": 0, "business": 0.0}),
             "by_prod": defaultdict(lambda: {"articles": 0, "business": 0.0})}


def merge3(a, b, c):
    return merge_offices(merge_offices(a, b), c)


def main():
    hier = load_hierarchy()
    print(f"Hierarchy: {len(hier):,} offices")

    print("Reading April CSVs...")
    apr_off, _, _ = read_productwise(APR_PROD)
    apr_mix = read_booktypewise(APR_BOOK)
    print(f"  Apr: {len(apr_off):,} active offices, {sum(r['articles'] for r in apr_off.values()):,} articles")

    print("Reading May CSVs...")
    may_off, _, _ = read_productwise(MAY_PROD)
    may_mix = read_booktypewise(MAY_BOOK)
    print(f"  May: {len(may_off):,} active offices, {sum(r['articles'] for r in may_off.values()):,} articles")

    print("Reading June CSVs...")
    jun_off, _, _ = read_productwise(JUN_PROD)
    jun_mix = read_booktypewise(JUN_BOOK)
    print(f"  Jun: {len(jun_off):,} active offices, {sum(r['articles'] for r in jun_off.values()):,} articles")

    print("Building Cumulative (Apr+May+Jun)...")
    all_oids = set(apr_off) | set(may_off) | set(jun_off)
    cum_off = {}
    for oid in all_oids:
        a = apr_off.get(oid) or empty_rec()
        b = may_off.get(oid) or empty_rec()
        c = jun_off.get(oid) or empty_rec()
        cum_off[oid] = merge3(a, b, c)

    cum_mix = defaultdict(lambda: {"walk_in": 0, "bulk_bnpl": 0, "postal_service": 0, "commercial": 0, "other": 0})
    for oid in set(apr_mix) | set(may_mix) | set(jun_mix):
        for k in ["walk_in", "bulk_bnpl", "postal_service", "commercial", "other"]:
            cum_mix[oid][k] = apr_mix.get(oid, {}).get(k, 0) + may_mix.get(oid, {}).get(k, 0) + jun_mix.get(oid, {}).get(k, 0)

    print("Building monthly scopes...")
    apr_pack = build_month("Apr 2026", apr_off, apr_mix, hier)
    may_pack = build_month("May 2026", may_off, may_mix, hier)
    jun_pack = build_month("Jun 2026", jun_off, jun_mix, hier)
    cum_pack = build_month("Apr-Jun 2026", cum_off, cum_mix, hier)

    BBM = {"Apr-26": apr_pack, "May-26": may_pack, "Jun-26": jun_pack, "Cumulative": cum_pack}

    for k, pack in BBM.items():
        c = pack["circle"]
        peak = c["peak_day"]["date"] if c["peak_day"] else "-"
        print(f"  {k}: circle {c['totals']['articles']:,} articles, {c['totals']['days']} days, peak {peak}")

    out = BASE / "_booking_by_month_june.json"
    out.write_text(json.dumps(BBM, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"\nWrote {out.name} ({out.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
