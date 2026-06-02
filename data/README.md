# Data folder

This folder contains the seed data + training data the app needs. Nothing here
is meant to be human-readable; these files are inputs to the regression model
and the optimizer.

## Files

| File | What it is | Used by |
| --- | --- | --- |
| `seattle_zones.json` | The 14 candidate placement zones with lat/lng centroids + the major venues in each zone. Hand-curated. | Geocoder, optimizer, map |
| `carts.json` | The fictional 6-cart fleet for "Emerald City Carts" + the Georgetown depot location. Edit this to change the operator's fleet. | RAG (`get_cart_fleet`), optimizer |
| `zone_spots.json` | 2-4 candidate micro-spots per zone with event-affinity scores. | Intra-zone spot picker |
| `historical_real.csv` | **3,280 rows of REAL Seattle activity data** from three public sources -- see below. | Regression training |
| `historical_events.csv` | **840 synthetic event-day rows** from `generate_history.py`. Teaches the regression event lift (real data has no event flags). | Regression training |
| `fetch_sdot.py` | Pulls SDOT pedestrian/bike counter data from data.seattle.gov + Open-Meteo historical weather. | Data refresh |
| `fetch_extra_sources.py` | Pulls Seattle Monorail daily ridership + Downtown Activation Plan quarterly data. Run AFTER fetch_sdot.py. | Data refresh |
| `generate_history.py` | Regenerates `historical_events.csv`. | Data refresh |

## What's actually in `historical_real.csv` (3,280 rows total)

Three real public Seattle datasets, all fetched live:

1. **SDOT pedestrian + bike counters** (`fetch_sdot.py`) -- 666 rows from 2024.
   Six counters across Burke-Gilman, Elliott Bay Trail, Broadway, Fremont
   Bridge, etc. Real daily counts joined with Open-Meteo historical weather.
   Honest limitation: trail/bridge sites, not commercial street corners.

2. **Seattle Center Monorail daily ridership** (`fetch_extra_sources.py`) --
   366 rows from calendar 2016 (the dataset stops there).
   Source: performance.seattle.gov dataset 88k3-9ct6.
   Real daily commercial-corridor activity (Westlake -> Seattle Center).
   Maps to seattle_center zone.

3. **Downtown Activation Plan Dashboard** (`fetch_extra_sources.py`) --
   25 quarters since 2019, expanded to ~2,250 daily rows.
   Source: cos-data.seattle.gov dataset d9ti-hi4p.
   This is **Seattle's official downtown foot-traffic data** -- worker +
   visitor + resident counts published by the city. Quarterly granularity,
   so we expand each quarter's average across its 90 days with a small
   weekend boost. Maps to downtown zone.

Combined: 3,280 real rows + 840 synthetic event rows = 4,120 total training rows.
Current fit: R² ~ 0.53, MAE ~ 1,600 pedestrians.

## To refresh the data

```bash
cd data
python fetch_sdot.py --start 2024-01-01 --end 2024-12-31
python fetch_extra_sources.py
python generate_history.py   # regenerate the synthetic event-day rows
```

## What we wanted but couldn't get for free

- **SafeGraph / Placer.ai** mobile-derived foot-traffic data: the gold standard
  but $$$. Production version of this app would buy it.
- **Daily street-level pedestrian counts at Pike Place / Lumen Field plazas**:
  Seattle does occasional intersection counts but not as a continuous API.
- **Sound Transit station boardings** at daily granularity: published as PDFs,
  not a clean queryable dataset.

The combination above is the best free-data version of "real Seattle activity
data" we could assemble.
