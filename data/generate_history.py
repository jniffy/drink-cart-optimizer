"""
Generates a synthetic-but-plausible historical foot-traffic dataset for Seattle zones.
Run once to (re)create historical_events.csv used to train the regression.

We don't have access to real pedestrian-counter data, so we encode well-known
Seattle dynamics (e.g., SoDo is dead unless there's a stadium event; Pike Place
is busy every weekend; weather has a big effect on outdoor zones).
"""
from __future__ import annotations
import csv
import json
import random
from pathlib import Path

DATA_DIR = Path(__file__).parent
random.seed(7)

zones = json.loads((DATA_DIR / "seattle_zones.json").read_text())["zones"]

EVENT_TYPES = ["none", "arena", "stadium", "theater", "music_venue", "convention", "festival"]
EVENT_DRAW = {                # rough additional foot-traffic from a nearby event
    "none": 0,
    "music_venue": 800,
    "theater": 1500,
    "convention": 2500,
    "arena": 5500,
    "festival": 7000,
    "stadium": 9000,
}

ROWS_PER_ZONE = 60            # ~14 zones * 60 = ~840 training rows


def synth_row(zone: dict) -> dict:
    dow = random.randint(0, 6)
    is_weekend = 1 if dow >= 5 else 0
    month = random.randint(1, 12)
    is_summer = 1 if month in (6, 7, 8) else 0

    # Seattle weather priors
    if month in (6, 7, 8):
        temp_f = random.gauss(72, 6)
        precip = max(0.0, random.gauss(0.10, 0.10))
    elif month in (12, 1, 2):
        temp_f = random.gauss(43, 5)
        precip = min(1.0, max(0.0, random.gauss(0.55, 0.20)))
    else:
        temp_f = random.gauss(56, 7)
        precip = min(1.0, max(0.0, random.gauss(0.35, 0.20)))

    event_type = random.choices(
        EVENT_TYPES,
        weights=[55, 8, 4, 12, 10, 6, 5],   # most days have no event
        k=1,
    )[0]

    # Stadium events almost only land in SoDo / U-District in real life
    if event_type == "stadium" and zone["id"] not in ("sodo", "u_district"):
        event_type = "none"
    if event_type == "arena" and zone["id"] not in ("seattle_center", "u_district"):
        event_type = random.choice(["none", "music_venue"])

    base = zone["base_foot_traffic"]
    weekend_boost = 1.25 if is_weekend else 1.0
    event_lift = EVENT_DRAW[event_type]
    weather_penalty = (1 - 0.55 * precip) * (1 + 0.004 * (temp_f - 55))
    summer_lift = 1.10 if is_summer else 1.0

    foot_traffic = (
        base * weekend_boost * weather_penalty * summer_lift + event_lift
    )
    foot_traffic *= random.gauss(1.0, 0.08)   # noise
    foot_traffic = max(200, int(foot_traffic))

    return {
        "zone_id": zone["id"],
        "day_of_week": dow,
        "is_weekend": is_weekend,
        "month": month,
        "is_summer": is_summer,
        "temperature_f": round(temp_f, 1),
        "precip_chance": round(precip, 2),
        "nearby_event_type": event_type,
        "base_foot_traffic": base,
        "foot_traffic": foot_traffic,
    }


def main() -> None:
    rows: list[dict] = []
    for zone in zones:
        for _ in range(ROWS_PER_ZONE):
            rows.append(synth_row(zone))

    out = DATA_DIR / "historical_events.csv"
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows -> {out}")


if __name__ == "__main__":
    main()
