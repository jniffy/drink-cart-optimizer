# Agentic Drink Cart Placement Optimizer — MVP

**MKTG 565 · Building Business Applications of LLMs · Joe McNiff & Austin Joyce**

An LLM-powered agent that decides where to deploy mobile drink carts in Seattle on any given day to maximize revenue. The agent searches the live web for events, predicts pedestrian foot traffic per neighborhood, runs a constrained non-linear optimizer over the cart fleet, and renders the plan on an interactive Google Map.

---

## 1. Quick start

If you already have Python 3.12+ and your two API keys, this is the whole flow:

```powershell
cd "C:\Users\<you>\OneDrive - UW\Spring26\Building Business Applications of LLMs\Project\mvp"
pip install -r requirements.txt
streamlit run app.py
```

Browser opens to `http://localhost:8501`. Paste your keys into the sidebar, pick a date, hit **Run optimization**.

To stop: `Ctrl+C` in PowerShell.

---

## 2. One-time setup (~15 min)

### a) Python 3.12 or 3.13
[python.org/downloads/windows](https://www.python.org/downloads/windows/) — **check "Add python.exe to PATH"** during install.

### b) OpenAI API key
1. [platform.openai.com/api-keys](https://platform.openai.com/api-keys) → **+ Create new secret key**
2. Copy the `sk-...` key immediately (you can't view it again)
3. New accounts: add ~$5 of credit at **Settings → Billing**. Each demo run costs cents.

### c) Google Maps API key (one key, four APIs)
1. [console.cloud.google.com](https://console.cloud.google.com/) → **New Project** → name it `cart-optimizer`
2. Enable all four APIs (search each in the top bar, hit **Enable**):
   - **Geocoding API** — venue name → lat/lng
   - **Routes API** — drive-time checks from depot
   - **Places API (New)** — nearby competition density (use the *(New)* one, not legacy)
   - **Maps JavaScript API** — embedded interactive map
3. **APIs & Services → Credentials → + Create Credentials → API key**, copy the `AIza...` key
4. Recommended: edit the key → **Restrict key** → check those four APIs → Save
5. Google requires a billing account, but the $200/month free tier easily covers this.

You now have one `sk-...` key and one `AIza...` key. Keep them handy.

---

## 3. Add your keys + run the demo

1. Open the app at `http://localhost:8501`
2. In the sidebar, paste your **OpenAI key** and **Google Maps key** into the password fields
3. Status badges turn green and the **Run optimization** button unlocks
4. Pick a target date, fleet size, and (optionally) the OpenAI model
5. Click **Run optimization** and watch the live agent trace stream in
6. When it finishes, explore the four result tabs:
   - **Summary** — agent's business-friendly write-up + placement table
   - **Map** — Google Maps view with foot-traffic heat layer + numbered cart pins
   - **Per-cart reasoning** — one card per cart explaining why it landed where it did
   - **Architecture & Methodology** — formulas, data sources, agentic loop, limitations

Keys live only in your browser session — they're never written to disk. Reload the page and you'll need to paste them again. (Optional: drop them in a `.env` file next to `app.py` to skip that step — see `.env.example`.)

---

## 4. Demo dates worth trying

| Date | What's interesting |
| --- | --- |
| **2026-06-15** | FIFA World Cup 2026 group-stage opener at Lumen Field. SoDo + Pioneer Square fan zones light up. **Marquee demo case.** |
| **2026-05-29** | Mariners home game + HONK! Fest in Georgetown + Wing Luke film festival. Multi-event Friday. |
| **2026-08-15** | Bumbershoot weekend at Seattle Center. Festival tag should dominate Seattle Center. |
| **2026-07-04** | Seafair / Independence Day. Multi-zone festival activity. |
| Any rainy weekday | Tests that the regression's rain-penalty term suppresses outdoor zones. |

---

## 5. File-by-file walkthrough

```
mvp/
├── app.py                    Streamlit UI: hero header, sidebar key inputs + run controls,
│                             KPI band, tabbed results (Summary / Map / Per-cart / Methodology)
├── agent.py                  OpenAI Responses API loop, 9 custom tools + hosted web search,
│                             auto-fallback to gpt-4o-mini, tool-call dedup, event-overrides validator
├── model.py                  sklearn LinearRegression: foot_traffic ~ weather + day + base + event_draw
├── optimizer.py              Two-stage constrained non-linear optimizer:
│                             (1) cart->zone enumeration with cannibalization penalty,
│                             (2) intra-zone micro-spot picker + deployment-window scheduler
│
├── tools/
│   ├── weather.py            Open-Meteo forecast (free), with seasonal-average fallback
│   ├── geocoding.py          Google Geocoding API: venue name -> lat/lng -> nearest zone
│   ├── routes.py             Google Routes API: drive/walk/transit time depot -> spot
│   ├── places.py             Google Places API (New): nearby coffee shops / cafes / restaurants
│   ├── inventory.py          Loads carts.json + supports n_carts override
│   ├── traffic.py            Wraps model.predict_all_zones, caches results for the optimizer
│   ├── placement.py          Wraps optimizer.optimize, falls back to cached predictions
│   ├── spots.py              Picks best intra-zone micro-spot based on event affinity
│   └── mapping.py            Generates the Google Maps JS embed HTML (cart pins + zone dots; heat layer via deck.gl GoogleMapsOverlay)
│
├── data/
│   ├── seattle_zones.json    14 placement zones + major venues (Lumen Field, Pike Place, etc.)
│   ├── carts.json            6-cart fleet for "Emerald City Carts" + Georgetown depot,
│   │                         each cart with inventory dict + named staff shifts
│   ├── zone_spots.json       2-4 candidate micro-spots per zone with event-affinity scores
│   ├── historical_real.csv   Real SDOT pedestrian counter rows joined with weather
│   ├── historical_events.csv Synthetic event-day rows that teach the regression event lift
│   ├── fetch_sdot.py         Pulls fresh SDOT counter data (run if you want to refresh)
│   └── generate_history.py   Regenerates the synthetic event-day rows
│
├── requirements.txt          Python dependencies
├── .env.example              Optional template for the API keys file
└── README.md                 You're reading it
```

---

## 6. The agent's loop (what's happening behind the scenes)

When you hit **Run optimization**, the agent executes this sequence:

1. **`web_search`** (OpenAI hosted) — searches the live web for "Seattle events <date> sports concerts cruise festivals". One call.
2. **`geocode_venue`** (Google Geocoding) — for each event venue found, returns lat/lng + which of our 14 zones it falls in. Also notes expected audience demographics (e.g. "Mariners game: family + 20–50 male-skewed", "World Cup: international + adult").
3. **`get_weather_forecast`** (Open-Meteo) — daily temperature + precip chance for Seattle.
4. **`get_cart_fleet`** — RAG over our internal `carts.json`. Returns the operator's cart roster (with inventory + staff shifts) and Georgetown depot location.
5. **`predict_foot_traffic`** — our trained regression. Critical: must include `event_overrides` mapping each event-bearing zone to its `event_type`. `agent.py` has a runtime validator that returns an error if `event_overrides` is missing — the agent self-corrects.
6. **`optimize_cart_placement`** — constrained non-linear optimizer that enumerates feasible cart-to-zone assignments, picks the best intra-zone micro-spot per cart, and assigns each cart a deployment window anchored on the event's typical peak hour.
7. **`get_route_time`** + **`find_nearby_competition`** (Google Routes + Places) — sanity checks on the top-revenue spots.
8. Final summary written to chat + structured plan rendered into the table + Google Maps view, with audience demographics carried through.

You can watch all of this happen live in the **"Agent live trace"** card at the top of the page.

---

## 7. The math (for the report)

**Foot-traffic prediction:**
```
foot_traffic = β1·day_of_week + β2·is_weekend + β3·month + β4·is_summer
             + β5·temperature_F + β6·precip_chance
             + β7·base_zone_traffic + β8·event_draw
             + intercept
```

Trained on real SDOT pedestrian-counter rows (Elliott Bay Trail, Downtown Activation Plan quarterly midpoints) plus synthetic event-day rows that teach event lift. Current fit: R² ≈ 0.47–0.60, MAE ≈ 1,000–1,200 pedestrians depending on data window. The R² is honest-low because real SDOT data has weather/seasonal noise we don't fully model — that's a feature, not a bug.

`event_draw` values: World Cup +18,000 · stadium game +9,000 · festival +7,000 · arena +5,500 · cruise call +4,500 · convention +2,500 · theater +1,500 · music venue +800.

**Revenue per cart:**
```
revenue = min(daily_capacity, 0.03 · foot_traffic) · avg_ticket_$
```
Where `daily_capacity = capacity_per_hour · max_hours`. The 3% conversion rate is a rough industry benchmark for street vendors. A second cart in the same zone gets its sales multiplied by 0.55 to account for cannibalization (the non-linear term).

**Spot selection:** for each (cart, zone) assignment, look up the zone's candidate micro-spots in `zone_spots.json`, score each spot's `event_affinity[event_type]`, and pick the highest. The optimizer also avoids placing two carts at the same micro-spot.

**Deployment schedule:** each cart's deploy window is anchored to the event's peak hour (e.g. World Cup → 18:00, festival → 13:00, cruise → 12:00), then clipped to the cart's operating window and capped by `max_hours`.

---

## 8. Known limitations (own these in the report)

1. **SDOT counters are trail/bridge counts, not commercial-corner pedestrian counts.** They capture weather/seasonal/weekday signals correctly but don't directly measure foot traffic at Pike Place or in front of Lumen Field. Production would augment with mobile-derived data (SafeGraph, Placer.ai, Veraset, Streetlight) or Sound Transit station ridership for an estimated R² lift to 0.75–0.85 and MAE drop below 600.
2. **The cart fleet ("Emerald City Carts") is fictional** — no real customer behind it. Easy to swap with a real operator's roster.
3. **Synthetic event-day rows** teach the model event lift because real SDOT data has no event flags. Production would tag historical days with their actual events to learn empirical lift.
4. **Conversion rate (3%) is a single industry-benchmark number.** A real operator would replace this with their own observed conversion from pedestrian traffic to drink sales.
5. **Optimizer is brute-force enumeration** over feasible assignments — fine at 6–8 carts × 14 zones, would need a real MIP solver (PuLP/CBC or Gurobi) at 50+ carts.

---

## 9. Demo Day talking points

- **Open with the live trace.** Hit Run on the World Cup date. Let the audience watch the agent web-search Ticketmaster + FIFA's site in real time.
- **Show the KPI band.** "$14,000 projected revenue from 6 carts, 5 of 6 placements driven by an event."
- **Click into the Map tab.** Show the heat layer + numbered cart pins. Click a pin for the InfoWindow popup.
- **Click into Per-cart reasoning.** Each card explains *why* that specific spot won — capacity-limited vs. demand-limited, cannibalization discount for the 2nd cart in a zone, deployment window anchored on the event's peak hour.
- **Click into Methodology.** This is your "we know our math" tab. Lists data sources, formula, RAG, conversion rate, and the production data upgrade path.
- **Close on limitations.** "We're upfront that SDOT counters are trail-based; production would buy SafeGraph data."

---

## 10. Troubleshooting

| Symptom | Fix |
| --- | --- |
| `streamlit: command not found` | Run `pip install -r requirements.txt` again |
| Run button stays disabled | Paste your OpenAI key in the sidebar — it unlocks once the key is set |
| Map tab is blank | Paste your Google Maps key in the sidebar; it must have **Maps JavaScript API** enabled in Google Cloud |
| `RateLimitError` / `insufficient_quota` | Out of OpenAI credit. Top up at platform.openai.com → Settings → Billing |
| `(max turns exceeded)` final message | Agent burned through its turn budget without finishing. Just hit Run again — usually finishes on the retry. Switching to `gpt-4o` (instead of mini) tends to follow the loop more crisply |
| Agent placements don't reflect events | The agent skipped `event_overrides`; the validator should catch and auto-retry. If it persists, re-run |
| Open-Meteo "400 Client Error" for far-future dates | Free forecast tier covers ~16 days out; the code falls back to seasonal averages automatically. Cosmetic only |
| Routes / Places tool returns "API not enabled" | You missed enabling that specific API in Google Cloud. Re-check section 2c |
| Port 8501 in use | Another Streamlit instance is running. Close that PowerShell window or kill the process in Task Manager |

---

## 11. Optional: refresh the real SDOT data

The repo ships with pre-built `historical_real.csv`, but if you want to pull fresh Seattle pedestrian-counter data:

```powershell
python data\fetch_sdot.py --start 2024-01-01 --end 2025-12-31
```

This re-pulls Elliott Bay Trail (daily counts) + Downtown Activation Plan (quarterly midpoints) joined with Open-Meteo historical weather, and overwrites `data\historical_real.csv`.

---

If anything's still confusing, ping Joe.
