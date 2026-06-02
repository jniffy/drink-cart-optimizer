"""
Pulls REAL Seattle foot-traffic data and writes the regression training CSV.

Three real public sources, all currently published by the City of Seattle:

  1. Elliott Bay Trail (Myrtle Edwards) -> belltown zone        SDOT, daily, 2024-2025
  2. MTS Trail W of I-90 Bridge         -> pioneer_square zone  SDOT, daily, 2024-2025
  3. Downtown Activation Plan dashboard -> downtown zone        Quarterly, 2019-2025

DAP is reduced to one row per quarter (midpoint date) so its 25 real data
points don't flood the regression with 2,250 near-identical daily expansions.

Burke-Gilman / Broadway / 26th SW / 39th NE / Spokane St were dropped: they
either turned bike-only after 2022 or stopped publishing data entirely.
"""
from __future__ import annotations
import argparse
import csv
import datetime as dt
import json
from pathlib import Path

import requests

DATA_DIR = Path(__file__).parent
OUT_CSV = DATA_DIR / "historical_real.csv"


SDOT_COUNTERS = [
    {
        "name": "Elliott Bay Trail (Myrtle Edwards)",
        "dataset": "4qej-qvrz",
        "zone": "belltown",
        "ped_fields": ["pedestrian_northbound", "pedestrian_southbound"],
    },
]


def _f(v):
    if v in (None, "", "null"):
        return 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def fetch_counter_daily(c, start, end):
    print(f"  fetching {c['name']} ...", flush=True)
    base = f"https://data.seattle.gov/resource/{c['dataset']}.json"
    daily = {}
    offset = 0
    page = 50000
    while True:
        params = {
            "$select": "date," + ",".join(c["ped_fields"]),
            "$where": f"date >= '{start}T00:00:00' AND date <= '{end}T23:59:59'",
            "$limit": page,
            "$offset": offset,
            "$order": "date",
        }
        r = requests.get(base, params=params, timeout=60)
        r.raise_for_status()
        rows = r.json()
        if not rows:
            break
        for row in rows:
            day = row["date"][:10]
            tot = sum(_f(row.get(f)) for f in c["ped_fields"])
            daily[day] = daily.get(day, 0) + int(tot)
        if len(rows) < page:
            break
        offset += page
    return daily


def fetch_dap_quarterly():
    """Downtown Activation Plan dashboard: real quarterly downtown foot-traffic."""
    print("  fetching Downtown Activation Plan quarterly foot-traffic ...", flush=True)
    url = "https://cos-data.seattle.gov/resource/d9ti-hi4p.json"
    r = requests.get(url, params={"$limit": 1000, "$order": "period"}, timeout=60)
    r.raise_for_status()
    out = []
    for item in r.json():
        period = (item.get("period") or "")[:10]
        worker = _f(item.get("worker_foot_traffic"))
        visitor = _f(item.get("visitor_foot_traffic"))
        resident = _f(item.get("residential_foot_traffic"))
        total = worker + visitor + resident
        if total > 0 and period:
            out.append({"period": period, "total_ft": int(total)})
    return out


def fetch_weather(start, end):
    print(f"  fetching weather {start} -> {end} ...", flush=True)
    url = (
        "https://archive-api.open-meteo.com/v1/archive"
        "?latitude=47.6062&longitude=-122.3321"
        "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
        "&temperature_unit=fahrenheit&timezone=America/Los_Angeles"
        f"&start_date={start}&end_date={end}"
    )
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    d = r.json()["daily"]
    out = {}
    for i, day in enumerate(d["time"]):
        tmax = d["temperature_2m_max"][i] or 0
        tmin = d["temperature_2m_min"][i] or 0
        psum = d["precipitation_sum"][i] or 0
        out[day] = {
            "temperature_f": round((tmax + tmin) / 2, 1),
            "precip_chance": round(min(1.0, psum / 10.0), 2),
        }
    return out


def build_sdot_rows(start, end, weather, zones_by_id):
    rows = []
    for c in SDOT_COUNTERS:
        daily_raw = fetch_counter_daily(c, start, end)
        zone = zones_by_id[c["zone"]]
        nonzero = sorted(v for v in daily_raw.values() if v > 0)
        if not nonzero:
            print(f"    {c['name']}: no nonzero days in window, skipping")
            continue
        median = nonzero[len(nonzero) // 2]
        scale = zone["base_foot_traffic"] / median if median else 1.0
        print(f"    {c['name']}: {len(daily_raw)} days, median={median}, scale={scale:.2f}")
        for day, count in daily_raw.items():
            if day not in weather or count <= 0:
                continue
            d = dt.date.fromisoformat(day)
            ft = int(count * scale)
            rows.append({
                "zone_id": c["zone"],
                "counter": c["name"],
                "date": day,
                "day_of_week": d.weekday(),
                "is_weekend": 1 if d.weekday() >= 5 else 0,
                "month": d.month,
                "is_summer": 1 if d.month in (6, 7, 8) else 0,
                "temperature_f": weather[day]["temperature_f"],
                "precip_chance": weather[day]["precip_chance"],
                "nearby_event_type": "none",
                "base_foot_traffic": zone["base_foot_traffic"],
                "foot_traffic": ft,
            })
    return rows


def build_dap_rows(weather, zones_by_id):
    """One row per quarter at the period midpoint. 25 quarters = 25 real
    downtown data points anchoring the regression's downtown baseline."""
    dap = fetch_dap_quarterly()
    if not dap:
        print("    DAP: no quarters returned, skipping")
        return []
    zone = zones_by_id["downtown"]
    daily_avgs = sorted(r["total_ft"] / 90 for r in dap if r["total_ft"] > 0)
    median = daily_avgs[len(daily_avgs) // 2]
    scale = zone["base_foot_traffic"] / median if median else 1.0
    print(f"    DAP: {len(dap)} quarters, median daily-avg={int(median)}, scale={scale:.4f}")

    rows = []
    for rec in dap:
        period_start = dt.date.fromisoformat(rec["period"])
        midpoint = period_start + dt.timedelta(days=45)
        day = midpoint.isoformat()
        if day not in weather:
            continue
        daily_avg = (rec["total_ft"] / 90) * scale
        rows.append({
            "zone_id": "downtown",
            "counter": "Downtown Activation Plan (quarterly midpoint)",
            "date": day,
            "day_of_week": midpoint.weekday(),
            "is_weekend": 1 if midpoint.weekday() >= 5 else 0,
            "month": midpoint.month,
            "is_summer": 1 if midpoint.month in (6, 7, 8) else 0,
            "temperature_f": weather[day]["temperature_f"],
            "precip_chance": weather[day]["precip_chance"],
            "nearby_event_type": "none",
            "base_foot_traffic": zone["base_foot_traffic"],
            "foot_traffic": int(daily_avg),
        })
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--start", default="2024-01-01")
    p.add_argument("--end",   default="2025-12-31")
    args = p.parse_args()

    print(f"Building real Seattle foot-traffic training set {args.start} -> {args.end}")
    zones = json.loads((DATA_DIR / "seattle_zones.json").read_text())["zones"]
    zones_by_id = {z["id"]: z for z in zones}

    weather = fetch_weather("2019-01-01", args.end)

    rows = build_sdot_rows(args.start, args.end, weather, zones_by_id)
    rows += build_dap_rows(weather, zones_by_id)

    if not rows:
        raise SystemExit("no rows fetched")
    fields = list(rows[0].keys())
    with OUT_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {OUT_CSV}")
    counts = {}
    for r in rows:
        counts[r['zone_id']] = counts.get(r['zone_id'], 0) + 1
    for z, c in sorted(counts.items()):
        print(f"    {z}: {c} rows")


if __name__ == "__main__":
    main()
