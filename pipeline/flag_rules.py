"""FLAG_RULES v1.0 — classifies each division x vertical against the
circle average for data/flags.json. Flat (not pipeline/derive/) since this
is thresholds/narrative logic, not a data-derivation step.

v1 emits ONLY below_avg flags — flags.json is a watch-list of
underperformers for the Overview attention strip, not a full above/below
matrix of every division x vertical combination (matches the "exception-
first" design already agreed for the Overview/vertical-page attention
strips).

Divisions/verticals with fy_target == 0 (e.g. RMS units against POSB/
PLI-RPLI, which have no real target) are skipped — otherwise they'd be
permanently flagged below_avg at 0% with a maxed-out streak, which is
noise, not signal.
"""
from datetime import datetime, timezone

RULES_VERSION = "1.0"

VERTICAL_LABELS = {
    "parcel": "Parcel", "mail_ops": "Mail Operations", "irgb": "IR & GB",
    "ccs": "CCS", "posb": "POSB", "pli_rpli": "PLI/RPLI",
}


def classify(division_pct: float, circle_avg_pct: float) -> str:
    """>= goes to above_avg — same tie-break convention as index.html's
    'Performance distribution' card (`x.composite >= avgComposite`)."""
    return "above_avg" if division_pct >= circle_avg_pct else "below_avg"


def compute_streak(division_monthly: list[dict], circle_monthly: list[dict]) -> int:
    """Consecutive months below THAT month's circle average, walking
    backward from the latest month."""
    streak = 0
    for div_m, cir_m in zip(reversed(division_monthly), reversed(circle_monthly)):
        if div_m["pct_prorata"] < cir_m["pct_prorata"]:
            streak += 1
        else:
            break
    return streak


def gap_cr(division_latest: dict) -> float:
    return round(max(0.0, division_latest["prorata_target"] - division_latest["achievement"]), 2)


def build_sentence(division_name, vertical_label, division_pct, circle_avg_pct, streak, gap):
    return (f"{division_name}: {division_pct:.0f}% of pro-rata in {vertical_label}, "
            f"below circle average for {streak} consecutive month{'s' if streak != 1 else ''}, "
            f"gap ₹{gap:.2f} Cr.")


def build_flags(trends: dict) -> dict:
    months = trends["meta"]["months"]
    circle_averages = {
        vkey: {"latest_pct_prorata": vdata["monthly"][-1]["pct_prorata"]}
        for vkey, vdata in trends["circle"]["verticals"].items()
    } if months else {}

    flags = []
    for div_slug, div in trends["divisions"].items():
        for vkey, vdata in div["verticals"].items():
            monthly = vdata["monthly"]
            if not monthly or vdata["fy_target"] == 0:
                continue
            latest = monthly[-1]
            circle_monthly = trends["circle"]["verticals"][vkey]["monthly"]
            circle_latest = circle_monthly[-1]
            severity = classify(latest["pct_prorata"], circle_latest["pct_prorata"])
            if severity != "below_avg":
                continue
            streak = compute_streak(monthly, circle_monthly)
            gap = gap_cr(latest)
            vertical_label = VERTICAL_LABELS[vkey]
            sentence = build_sentence(div["name"], vertical_label, latest["pct_prorata"],
                                       circle_latest["pct_prorata"], streak, gap)
            flags.append({
                "id": f"{vkey}-{div_slug}-{latest['month']}",
                "division": div_slug,
                "division_name": div["name"],
                "region": div["region"],
                "vertical": vkey,
                "severity": severity,
                "latest_pct_prorata": round(latest["pct_prorata"], 1),
                "circle_avg_pct_prorata": round(circle_latest["pct_prorata"], 1),
                "gap_cr": gap,
                "streak_months_below_avg": streak,
                "sentence": sentence,
                "link": f"#drilldown?div={div_slug}&vertical={vkey}",
            })

    return {
        "meta": {
            "generated_on": datetime.now(timezone.utc).isoformat(),
            "data_as_on": months[-1] if months else None,
            "rules_version": RULES_VERSION,
        },
        "circle_averages": circle_averages,
        "flags": flags,
    }
