#!/usr/bin/env python3
"""assemble.py — combines every month's data/dataset_<YYYY-MM>.json into
the single data/latest.json the dashboard's async loader fetches.

This is the ONLY place *_BY_MONTH structures get assembled from per-month
slices; build_dataset.py only ever writes one month's one section at a
time. Run this after any build_dataset.py call that changes a section
(the GitHub Action does this automatically — see Phase 4), or standalone
to rebuild data/latest.json from whatever's currently in data/dataset_*.json.

Top-level keys match the JS global names index.html's loader assigns them
to directly (POSB_BY_MONTH, PLI_POLICIES, ...), so the loader is a thin
assignment layer, not a reshaping one.

Usage: python assemble.py
"""
import json
from pathlib import Path

from pipeline.config import load_config
from pipeline.common import iso_to_label
from pipeline.sections import booking as booking_mod
from pipeline.derive import subdiv_bolookup, office_status, subdiv_booking, pli_rpli_cum

BASE = Path(__file__).parent
DATA_DIR = BASE / "data"


def _available_months() -> list[str]:
    return sorted(p.stem.removeprefix("dataset_") for p in DATA_DIR.glob("dataset_*.json"))


def _load_dataset(month_iso: str) -> dict:
    p = DATA_DIR / f"dataset_{month_iso}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"sections": {}}


def _standalone(dataset: dict, section_name: str):
    section = dataset["sections"].get(section_name)
    return section["standalone"] if section else None


def _assemble_posb_by_month(months: list[str]) -> dict:
    out = {}
    for month in months:
        posb = _standalone(_load_dataset(month), "posb")
        if posb:
            out[iso_to_label(month)] = posb["divisions"]
    return out


def _assemble_pli_rpli(months: list[str], segment: str) -> dict:
    out = {}
    for month in months:
        section = _standalone(_load_dataset(month), segment)
        if section:
            out[iso_to_label(month)] = section["divisions"]
    out["__CUM__"] = pli_rpli_cum.build_cum(months, segment)
    return out


def _assemble_booking_by_month(months: list[str]) -> dict:
    out = {}
    packs = []
    for month in months:
        booking = _standalone(_load_dataset(month), "booking")
        if not booking:
            continue
        label = iso_to_label(month)
        out[label] = {k: v for k, v in booking.items() if k not in ("by_office", "mix_by_office")}
        packs.append(booking)
    if packs:
        out["Cumulative"] = booking_mod.build_cumulative_pack(packs)
    return out


def _assemble_ecr_by_month(months: list[str]) -> dict:
    """For patching DATA_BY_MONTH in the JS loader. April stays static
    (hand-authored OFFICE_ENTRIES/targets, a closed month that won't be
    reuploaded) — the loader itself skips 'Apr-26' when applying these,
    so it's harmless (but wasteful) to include it here too; kept out for
    clarity about what's actually "live" data."""
    out = {}
    for month in months:
        ecr = _standalone(_load_dataset(month), "ecr")
        label = iso_to_label(month)
        if ecr and label != "Apr-26":
            out[label] = ecr["divisions"]
    return out


def _assemble_circle_full(months: list[str]):
    """Single snapshot (not month-keyed) — whichever month was most
    recently built wins, matching the legacy patch script's behavior of
    simply overwriting the one CIRCLE_FULL constant each month."""
    for month in reversed(months):
        ecr = _standalone(_load_dataset(month), "ecr")
        if ecr and "circle_full" in ecr:
            return ecr["circle_full"]
    return None


def assemble() -> dict:
    cfg = load_config()
    months = _available_months()
    print(f"Assembling from months: {months}")

    print("POSB_BY_MONTH...")
    posb_by_month = _assemble_posb_by_month(months)

    print("PLI_POLICIES / RPLI_POLICIES...")
    pli_policies = _assemble_pli_rpli(months, "pli")
    rpli_policies = _assemble_pli_rpli(months, "rpli")

    print("BOOKING_BY_MONTH (incl. cross-month Cumulative rebuild)...")
    booking_by_month = _assemble_booking_by_month(months)

    print("ECR_BY_MONTH (for DATA_BY_MONTH patching) + CIRCLE_FULL...")
    ecr_by_month = _assemble_ecr_by_month(months)
    circle_full = _assemble_circle_full(months)

    print("SUBDIV_DATA + BO_LOOKUP...")
    sub_bo = subdiv_bolookup.build(cfg, months)

    print("OFFICE_STATUS_BY_MONTH...")
    office_status_by_month = office_status.build(months)

    print("SUBDIV_BOOKING...")
    subdiv_booking_out = subdiv_booking.build(cfg, months)

    return {
        "generated_from_months": months,
        "POSB_BY_MONTH": posb_by_month,
        "PLI_POLICIES": pli_policies,
        "RPLI_POLICIES": rpli_policies,
        "BOOKING_BY_MONTH": booking_by_month,
        "ECR_BY_MONTH": ecr_by_month,
        "CIRCLE_FULL": circle_full,
        "SUBDIV_DATA": sub_bo["subdiv_data"],
        "BO_LOOKUP": sub_bo["bo_lookup"]["lookup"],
        "BO_SEARCH": sub_bo["bo_lookup"]["index"],
        "OFFICE_STATUS_BY_MONTH": office_status_by_month,
        "SUBDIV_BOOKING": subdiv_booking_out,
    }


def main():
    result = assemble()
    DATA_DIR.mkdir(exist_ok=True)
    out_path = DATA_DIR / "latest.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"\nWrote {out_path} ({out_path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
