"""SUBDIV_BOOKING — sub-division booking breakdown cards (HOs/SOs/BOs with
article/revenue totals) on the Booking tab.

Ported from build_subdiv_booking.py, which had two real problems fixed
here rather than reproduced: (1) it read a single un-dated
uploads/booking_productwise.csv with a hardcoded path to a different
machine, so it was frozen on April-2026-only data forever; (2) the
renderer (renderSubdivBreakdown in index.html) never varied with the
Booking tab's own month switcher, so switching to May/June silently kept
showing April's numbers — an unnoticed staleness bug, not a design
choice. Per explicit direction, this version is month-keyed
(Apr-26/May-26/Jun-26/Cumulative, same shape as BOOKING_BY_MONTH) so the
loader/renderer can make it follow the month switcher; see Phase 2e for
the matching index.html change.

Uses the master roster (not office_hierarchy.json) for the office
universe/type, consistent with SUBDIV_DATA's own office set.
"""
import json
from pathlib import Path
from collections import defaultdict

from pipeline.common import Roster, iso_to_label

BASE = Path(__file__).parent.parent.parent
DATA_DIR = BASE / "data"

TYPE_MAP = {"HPO": "HOs", "SPO": "SOs", "BPO": "BOs"}


def _load_booking_by_office(month_iso: str) -> dict:
    p = DATA_DIR / f"dataset_{month_iso}.json"
    if not p.exists():
        return {}
    dataset = json.loads(p.read_text(encoding="utf-8"))
    section = dataset["sections"].get("booking")
    return section["standalone"].get("by_office", {}) if section else {}


def _build_one(roster_offices: dict, by_off: dict) -> dict:
    structure = defaultdict(lambda: defaultdict(lambda: {"HOs": [], "SOs": [], "BOs": []}))
    for oid, info in roster_offices.items():
        slot = TYPE_MAP.get(info["type"])
        if slot is None:
            continue
        div, subdiv = info["division"], info["sub_division"]
        bk = by_off.get(oid, {"articles": 0, "business": 0.0})
        structure[div][subdiv][slot].append({
            "id": oid, "name": info["name"],
            "articles": int(round(bk["articles"])),
            "revenue": round(bk["business"], 2),
        })

    for div in structure:
        for subdiv in structure[div]:
            for slot in ("HOs", "SOs", "BOs"):
                structure[div][subdiv][slot].sort(key=lambda x: (x["articles"], x["id"]))

    out = {}
    for div, subdivs in sorted(structure.items()):
        out[div] = {sd: dict(slots) for sd, slots in sorted(subdivs.items())}
    return out


def build(cfg: dict, months: list[str]) -> dict:
    roster = Roster.load(cfg)

    result = {}
    cum_off = defaultdict(lambda: {"articles": 0, "business": 0.0})
    for month in months:
        by_off = _load_booking_by_office(month)
        label = iso_to_label(month)
        result[label] = _build_one(roster.offices, by_off)
        for oid, rec in by_off.items():
            cum_off[oid]["articles"] += rec["articles"]
            cum_off[oid]["business"] += rec["business"]

    result["Cumulative"] = _build_one(roster.offices, dict(cum_off))
    return result
