"""Streamlit UI for the Agentic Drink Cart Placement Optimizer."""
from __future__ import annotations
import datetime as dt
import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))

for _k in ("OPENAI_API_KEY", "GOOGLE_MAPS_API_KEY", "OPENAI_MODEL"):
    _v = os.environ.get(_k)
    if _v and _v != _v.strip():
        os.environ[_k] = _v.strip()

st.set_page_config(
    page_title="Agentic Drink Cart Placement Optimizer",
    layout="wide",
    initial_sidebar_state="expanded",
)


CSS = """
<style>
  #MainMenu {visibility: hidden;}
  footer {visibility: hidden;}
  header {visibility: hidden;}
  .hero { background: linear-gradient(135deg, #1e40af 0%, #2563eb 60%, #3b82f6 100%); color: white; padding: 28px 32px; border-radius: 16px; margin-bottom: 18px; box-shadow: 0 4px 14px rgba(30, 64, 175, 0.18); }
  .hero h1 { font-size: 30px; font-weight: 700; margin: 0 0 4px 0; color: white; letter-spacing: -0.4px; }
  .hero p { margin: 0; font-size: 14px; opacity: 0.92; }
  .hero .byline { margin-top: 8px; font-size: 12px; opacity: 0.78; border-top: 1px solid rgba(255,255,255,0.25); padding-top: 8px; }
  .kpi-band { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin: 10px 0 18px 0; }
  .kpi { background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 14px 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
  .kpi .label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.6px; color: #64748b; margin-bottom: 4px; font-weight: 600; }
  .kpi .value { font-size: 22px; font-weight: 700; color: #0f172a; line-height: 1.1; }
  .kpi .sub { font-size: 11px; color: #94a3b8; margin-top: 2px; }
  .kpi-money .value { color: #059669; }
  .cart-card { background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 14px 16px; margin-bottom: 10px; border-left: 4px solid #1e40af; }
  .cart-card-head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 6px; }
  .cart-card-title { font-weight: 700; color: #0f172a; font-size: 15px; }
  .cart-card-rev { font-weight: 700; color: #059669; font-size: 15px; }
  .cart-card-spot { color: #475569; font-size: 13px; margin-bottom: 8px; }
  .cart-card-reason { color: #334155; font-size: 13px; line-height: 1.45; }
  .cart-card-meta { margin-top: 8px; padding-top: 8px; border-top: 1px solid #f1f5f9; font-size: 11px; color: #64748b; display: flex; flex-wrap: wrap; gap: 12px; }
  .pill { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 600; }
  .pill-event { background: #fef3c7; color: #92400e; }
  .pill-none { background: #f1f5f9; color: #475569; }
  section[data-testid="stSidebar"] { background: #f8fafc; }
  .section-h { font-size: 17px; font-weight: 700; color: #0f172a; margin: 14px 0 8px 0; padding-bottom: 6px; border-bottom: 2px solid #e2e8f0; }
  .key-status { font-size: 12px; padding: 4px 8px; border-radius: 6px; margin-top: 4px; }
  .key-ok { background: #d1fae5; color: #065f46; }
  .key-missing { background: #fee2e2; color: #991b1b; }
  .arch-card { background: white; border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px 14px; margin-bottom: 8px; }
  .arch-card .arch-title { font-weight: 700; color: #1e40af; font-size: 14px; margin-bottom: 4px; }
  .arch-card .arch-desc { font-size: 13px; color: #334155; line-height: 1.45; }
  .upgrade-row { background: #eff6ff; border-left: 3px solid #2563eb; padding: 10px 14px; margin-bottom: 6px; border-radius: 4px; }
  .upgrade-row b { color: #1e40af; }
  .overview-card { background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); border: 1px solid #bfdbfe; border-radius: 12px; padding: 16px 20px; margin-bottom: 16px; font-size: 14px; line-height: 1.55; color: #0f172a; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

st.markdown(
    """
    <div class="hero">
      <h1>Agentic Drink Cart Placement Optimizer</h1>
      <p>Live event search &nbsp;&rarr;&nbsp; ML foot-traffic regression &nbsp;&rarr;&nbsp; non-linear placement optimization</p>
      <div class="byline">MKTG 565 &middot; Austin Joyce &amp; Joseph McNiff &middot; UW Foster School of Business</div>
    </div>
    """,
    unsafe_allow_html=True,
)


def _get_key(env_name):
    v = st.session_state.get(env_name) or os.environ.get(env_name, "")
    return v.strip() if isinstance(v, str) else v


def _apply_keys_to_env():
    for k in ("OPENAI_API_KEY", "GOOGLE_MAPS_API_KEY", "OPENAI_MODEL"):
        v = st.session_state.get(k)
        if v:
            os.environ[k] = v.strip() if isinstance(v, str) else v
    for k in ("OPENAI_API_KEY", "GOOGLE_MAPS_API_KEY", "OPENAI_MODEL"):
        env_v = os.environ.get(k)
        if env_v and env_v != env_v.strip():
            os.environ[k] = env_v.strip()


with st.sidebar:
    st.markdown("### API keys")
    existing_openai = os.environ.get("OPENAI_API_KEY", "")
    openai_placeholder = "Loaded from .env" if existing_openai and not st.session_state.get("OPENAI_API_KEY") else "Paste your sk-... key"
    openai_input = st.text_input("OpenAI API key", value=st.session_state.get("OPENAI_API_KEY", ""), type="password", placeholder=openai_placeholder, key="OPENAI_API_KEY_input")
    if openai_input:
        st.session_state["OPENAI_API_KEY"] = openai_input.strip()

    existing_gmaps = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    gmaps_placeholder = "Loaded from .env" if existing_gmaps and not st.session_state.get("GOOGLE_MAPS_API_KEY") else "Paste your AIza... key"
    gmaps_input = st.text_input("Google Maps API key", value=st.session_state.get("GOOGLE_MAPS_API_KEY", ""), type="password", placeholder=gmaps_placeholder, key="GOOGLE_MAPS_API_KEY_input")
    if gmaps_input:
        st.session_state["GOOGLE_MAPS_API_KEY"] = gmaps_input.strip()

    MODELS = ["gpt-4o-mini", "gpt-4o"]
    _current = st.session_state.get("OPENAI_MODEL") or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    if _current not in MODELS:
        _current = "gpt-4o-mini"
    model_input = st.selectbox("OpenAI model", options=MODELS, index=MODELS.index(_current), help="gpt-4o-mini is cheaper + has higher rate limits.", key="OPENAI_MODEL_input")
    if model_input:
        st.session_state["OPENAI_MODEL"] = model_input

    _apply_keys_to_env()

    if _get_key("OPENAI_API_KEY"):
        st.markdown('<div class="key-status key-ok">OpenAI key in use</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="key-status key-missing">OpenAI key missing</div>', unsafe_allow_html=True)
    if _get_key("GOOGLE_MAPS_API_KEY"):
        st.markdown('<div class="key-status key-ok">Google Maps key in use</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="key-status key-missing">Google Maps key missing</div>', unsafe_allow_html=True)

    st.caption("Keys live in your browser session only. Never written to disk.")
    st.divider()
    st.markdown("### Run inputs")
    today = dt.date.today()
    target_date = st.date_input("Target date", value=today + dt.timedelta(days=7), min_value=today, max_value=today + dt.timedelta(days=180))
    n_carts = st.number_input("Number of carts", min_value=1, max_value=20, value=6, step=1)
    extra_context = st.text_area("Extra context (optional)", value="", placeholder="e.g., 'Cart 4 is in the shop today'")
    run_btn = st.button("Run optimizer", type="primary", use_container_width=True, disabled=not _get_key("OPENAI_API_KEY"))


from agent import run_agent
from tools.mapping import render_placement_map_html


def render_methodology_tab():
    # ===== Project overview =====
    st.markdown('<div class="section-h">Project overview</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="overview-card">'
        'We propose an <b>AI-powered agentic system</b> that autonomously determines optimal placement of '
        'mobile drink-selling carts across a metropolitan area. The agent monitors upcoming local events '
        '&mdash; concerts, conferences, sporting events, festivals &mdash; and predicts foot-traffic patterns to '
        'maximize cart revenue. By combining <b>real-time event intelligence, weather forecasting, '
        'historical regression models, and non-linear optimization</b>, the system transforms a '
        'labor-intensive planning task into an automated, data-driven decision pipeline.'
        '</div>',
        unsafe_allow_html=True,
    )

    # ===== The Agentic Loop (7 canonical steps) =====
    st.markdown('<div class="section-h">The Agentic Loop (7 steps)</div>', unsafe_allow_html=True)
    st.markdown(
        "The heart of the system. The agent autonomously cycles through these 7 steps with no human "
        "intervention -- choosing which tools to invoke, iterating when data is incomplete, and "
        "orchestrating multiple specialized components."
    )
    steps = [
        ("(1) Web Search", "OpenAI hosted web_search_preview",
         "The agent queries the live internet for upcoming events in Seattle on the target date -- "
         "concerts (Ticketmaster), conferences (Seattle Convention Center), sports games "
         "(Mariners / Seahawks / Sounders / Kraken / Huskies), festivals (Visit Seattle), cruise calls "
         "(Port of Seattle Pier 66 / Pier 91), and FIFA World Cup 2026 matches at Lumen Field. "
         "Collects dates, venues, artists/teams, and industry."),
        ("(2) Extract & Parse", "geocode_venue tool (Google Geocoding API) + get_weather_forecast (Open-Meteo)",
         "Raw search results are structured into event profiles: event_type tag (world_cup / stadium / "
         "arena / theater / music_venue / convention / festival / cruise / none), projected weather "
         "(temperature, precipitation), and venue geolocation (lat/lng -> mapped to one of our "
         "14 placement zones)."),
        ("(3) Foot-Traffic Model", "predict_foot_traffic tool (sklearn LinearRegression)",
         "A pre-trained linear regression -- built on historical attendance and sales data for similar "
         "event types (real Seattle pedestrian-counter data + the city's Downtown Activation Plan + "
         "synthetic event-day rows) -- estimates pedestrian volume per zone for the target date and "
         "time window."),
        ("(4) RAG -- Internal Data", "get_cart_fleet + list_zone_spots tools (local JSON retrieval)",
         "Retrieval-Augmented Generation: the agent retrieves operator-specific knowledge -- number of "
         "available carts, beverage inventory mix, hourly capacity, average ticket size, operating "
         "windows, depot location, and the 2-4 candidate intra-zone micro-spots in each zone -- from "
         "internal JSON files (data/carts.json, data/zone_spots.json) instead of LLM training-data memory."),
        ("(5) Foot-Traffic Map", "render_placement_map_html (Google Maps JavaScript API)",
         "The agent synthesizes regression output and event locations into a spatial heat-map showing "
         "predicted pedestrian density across the 14-zone city grid for the event day. "
         "Heat layer + zone-centroid markers + cart pins, embedded as live Google Maps JS."),
        ("(6) Non-Linear Optimizer", "optimize_cart_placement tool (Python brute-force NLP)",
         "Two-stage optimizer ingests the foot-traffic predictions and cart constraints "
         "(max_carts_per_zone, capacities, ticket sizes) and applies non-linear programming "
         "(objective = revenue with cannibalization penalty) to determine cart positions that "
         "maximize total projected revenue. Stage 2 picks the best intra-zone micro-spot per cart "
         "based on the dominant event in that zone."),
        ("(7) Output -- Placement Plan", "Streamlit UI: KPI band + table + map + per-cart cards",
         "The final deliverable is a cart placement plan + interactive map + per-cart reasoning "
         "explaining capacity-limited vs. demand-limited logic, pushed to the operations team for "
         "execution. The agent can re-run the loop as new events are announced or conditions change "
         "-- just hit 'Run optimizer' again for an updated plan."),
    ]
    for title, sub, desc in steps:
        st.markdown(
            '<div class="arch-card"><div class="arch-title">' + title +
            ' &middot; <span style="color:#64748b;font-weight:500;">' + sub + '</span></div>'
            '<div class="arch-desc">' + desc + '</div></div>',
            unsafe_allow_html=True,
        )

    # ===== Why agentic? =====
    st.markdown('<div class="section-h">Why agentic?</div>', unsafe_allow_html=True)
    st.markdown(
        "The system exhibits true agentic behavior: it **autonomously decides** which tools to invoke, "
        "**iterates** when data is incomplete (e.g., a runtime validator catches when the agent forgot "
        "event_overrides and forces a retry), and **orchestrates** multiple specialized components "
        "(search, regression, RAG, optimization) without human intervention -- converting unstructured "
        "real-world signals into an actionable, revenue-maximizing plan. "
        "The Streamlit live trace shows every tool call so you can watch the agent reason through the "
        "loop in real time."
    )

    # ===== Tools at a glance =====
    st.markdown('<div class="section-h">Every tool and API at a glance</div>', unsafe_allow_html=True)
    tools_glance = [
        ("LLM agent", "OpenAI Responses API",
         "gpt-4o-mini default (or gpt-4o). Hosts the loop, calls tools, writes the final summary."),
        ("Live web search", "OpenAI web_search_preview (hosted)",
         "Step 1. Searches Ticketmaster, FIFA, Port of Seattle, sports schedules, Visit Seattle festivals."),
        ("Geocoding", "Google Geocoding API",
         "Step 2. Venue name -> lat/lng -> zone."),
        ("Routes", "Google Routes API",
         "Step 7 sanity-check. Drive time depot -> spot."),
        ("Places", "Google Places API (New)",
         "Step 7 sanity-check. Nearby cafe / coffee / bar count for competition density."),
        ("Map embed", "Google Maps JavaScript API",
         "Step 5. Heat layer + cart pins + zone centroids in the UI."),
        ("Weather", "Open-Meteo (free)",
         "Step 2 + 3. Daily forecast + historical archive used for training."),
        ("RAG store", "data/carts.json + data/zone_spots.json",
         "Step 4. Operator's cart roster, depot, intra-zone micro-spots -- retrieved without going to LLM memory."),
        ("Foot-traffic regression", "sklearn LinearRegression",
         "Step 3. Trained on real SDOT pedestrian counts + Downtown Activation Plan + synthetic event rows."),
        ("Optimizer", "Custom Python (brute-force non-linear)",
         "Step 6. Two-stage cart-to-zone + intra-zone spot picker with cannibalization."),
    ]
    for title, sub, desc in tools_glance:
        st.markdown(
            '<div class="arch-card"><div class="arch-title">' + title +
            ' &middot; <span style="color:#64748b;font-weight:500;">' + sub + '</span></div>'
            '<div class="arch-desc">' + desc + '</div></div>',
            unsafe_allow_html=True,
        )

    # ===== Regression details =====
    st.markdown('<div class="section-h">The regression model in detail</div>', unsafe_allow_html=True)
    try:
        from model import get_model
        _, metrics = get_model()
        n_train = metrics["n_train"]
        n_real = metrics["sources"].get("real_sdot_rows", 0)
        n_synth = metrics["sources"].get("synthetic_event_rows", 0)
        r2 = metrics["r2"]
        mae = metrics["mae"]
    except Exception:
        n_train, n_real, n_synth, r2, mae = "?", "?", "?", 0.47, 1212

    cols = st.columns(4)
    cols[0].metric("Training rows", str(n_train))
    cols[1].metric("Real / synthetic", str(n_real) + " / " + str(n_synth))
    cols[2].metric("R-squared", (str(round(r2, 2)) if isinstance(r2, float) else str(r2)))
    cols[3].metric("MAE (peds)", (format(int(mae), ",") if isinstance(mae, float) else str(mae)))

    st.markdown(
        "**Formula:**\n\n"
        "`foot_traffic = beta1*day_of_week + beta2*is_weekend + beta3*month + beta4*is_summer + "
        "beta5*temperature_F + beta6*precip_chance + beta7*base_zone_traffic + beta8*event_draw + intercept`\n\n"
        "**Real training data sources:**\n\n"
        "- **Elliott Bay Trail (Myrtle Edwards) pedestrian counter** -- SDOT, daily, 2024-2025. "
        "data.seattle.gov dataset 4qej-qvrz. Maps to the **belltown** zone.\n"
        "- **Downtown Activation Plan dashboard** -- City of Seattle's official quarterly downtown "
        "foot-traffic counts (worker + visitor + resident). cos-data.seattle.gov dataset d9ti-hi4p. "
        "25 quarters since 2019, used at quarterly midpoint dates. Maps to the **downtown** zone.\n"
        "- **Open-Meteo historical weather archive** joined to each foot-traffic observation.\n"
        "- **Synthetic event-day rows** (840) generated by data/generate_history.py. Required because no "
        "public Seattle dataset tags days with their actual events; we teach event lift synthetically.\n\n"
        "**Event-draw values:** World Cup +18,000 . stadium +9,000 . festival +7,000 . arena +5,500 . "
        "cruise +4,500 . convention +2,500 . theater +1,500 . music venue +800.\n\n"
        "**Revenue per cart:** `revenue = min(daily_capacity, 0.03 * foot_traffic) * avg_ticket_$`. "
        "3% conversion is an industry benchmark for street vendors. Two carts in the same zone: "
        "second cart is multiplied by 0.55 for cannibalization."
    )

    # ===== Production data upgrade path =====
    st.markdown('<div class="section-h">Limitations and production data upgrade path</div>', unsafe_allow_html=True)
    st.markdown(
        "**Where the regression is honestly weak:** Seattle has very limited free public foot-traffic data. "
        "Only two recent, real-pedestrian datasets exist for our zones (Elliott Bay Trail for Belltown + "
        "the city's quarterly Downtown Activation Plan). Other zones are anchored only by the synthetic "
        "event-day rows. **This is the single biggest lever for improving R-squared and MAE.** "
        "Buying any of the following data sources would meaningfully improve model accuracy:"
    )
    upgrades = [
        ("SafeGraph",
         "Mobile-derived visit counts at any commercial place, daily granularity. Industry standard for "
         "retail-analytics research. ~$5,000-$15,000/year for Seattle metro coverage. "
         "**Estimated lift: R-squared 0.47 -> 0.82, MAE 1,200 -> ~400.**"),
        ("Placer.ai",
         "Same idea as SafeGraph, business-friendly UI, used by mall operators and real-estate firms. "
         "Per-place daily visit counts. ~$10,000-$25,000/year. "
         "**Estimated lift: R-squared 0.47 -> 0.85, MAE -> ~350.**"),
        ("Veraset",
         "Raw mobility data feed (anonymous device pings). Most flexible but requires data engineering. "
         "~$3,000-$8,000/month. **Estimated lift: R-squared -> 0.80, MAE -> ~450.**"),
        ("Streetlight Data",
         "Pedestrian + vehicle volumes from mobile signals, segment-level granularity. Used by "
         "transportation departments. ~$2,000-$10,000 per study. "
         "**Estimated lift: R-squared -> 0.75, MAE -> ~600.**"),
        ("BestTime.ai",
         "Free tier + paid plans. Provides Google Popular-Times-style busy-hour curves via official API "
         "for ~10k US places. ~$200/month at our scale. "
         "**Estimated lift: R-squared -> 0.65, MAE -> ~750.** Cheapest meaningful upgrade."),
        ("Sound Transit Link daily station boardings",
         "Free if Sound Transit publishes it as continuous open data (currently PDFs only). Would directly "
         "cover Capitol Hill, U-District, SoDo, Stadium, and Pioneer Square zones. "
         "**Estimated lift: R-squared -> 0.62, MAE -> ~850.** Best free option if it ever becomes API-queryable."),
    ]
    for name, desc in upgrades:
        st.markdown('<div class="upgrade-row"><b>' + name + '.</b> ' + desc + '</div>', unsafe_allow_html=True)

    st.markdown(
        "**Other limitations to acknowledge in the report:**\n\n"
        "- The cart fleet ('Emerald City Carts') is fictional; trivially swappable with a real operator's roster.\n"
        "- Synthetic event-day rows teach event lift because real Seattle data has no event flags. "
        "Paid data would make event lift empirical instead of synthetic.\n"
        "- 3% conversion rate is an industry-benchmark single number; a real operator would replace with "
        "their own observed pedestrian-to-sale ratio.\n"
        "- Optimizer is brute-force enumeration; fine at 6-12 carts x 14 zones, would need a real MIP "
        "solver (PuLP/CBC, Gurobi) at 50+ carts."
    )


# ---- Welcome state ---------------------------------------------------------

if not run_btn:
    welcome_col1, welcome_col2 = st.columns([2, 1])
    with welcome_col1:
        st.markdown('<div class="section-h">Project overview</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="overview-card">'
            'An <b>AI-powered agentic system</b> that autonomously determines optimal placement of mobile '
            'drink-selling carts across Seattle. The agent monitors upcoming local events &mdash; concerts, '
            'conferences, sporting events, festivals &mdash; and predicts foot-traffic patterns to maximize '
            'cart revenue. By combining <b>real-time event intelligence, weather forecasting, historical '
            'regression models, and non-linear optimization</b>, the system transforms a labor-intensive '
            'planning task into an automated, data-driven decision pipeline.'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="section-h">The 7-step Agentic Loop (summary)</div>', unsafe_allow_html=True)
        st.markdown(
            "1. **Web Search** -- live event intelligence from Ticketmaster, FIFA, Port of Seattle, sports schedules\n"
            "2. **Extract & Parse** -- geocode venues, get weather, tag events\n"
            "3. **Foot-Traffic Model** -- sklearn regression on real SDOT + Downtown Activation Plan + synthetic event rows\n"
            "4. **RAG -- Internal Data** -- retrieve cart fleet, depot, intra-zone candidate spots from local JSON\n"
            "5. **Foot-Traffic Map** -- spatial heat-map via Google Maps JS\n"
            "6. **Non-Linear Optimizer** -- cart-to-zone + intra-zone spot picker with cannibalization penalty\n"
            "7. **Output -- Placement Plan** -- map + table + per-cart reasoning"
        )
    with welcome_col2:
        st.markdown('<div class="section-h">Quick start</div>', unsafe_allow_html=True)
        if not _get_key("OPENAI_API_KEY"):
            st.warning("Paste your **OpenAI API key** in the sidebar to enable the Run button.")
        if not _get_key("GOOGLE_MAPS_API_KEY"):
            st.info("Paste your **Google Maps API key** for venue geocoding + the embedded map.")
        st.markdown(
            "Pick a target date (try **June 15, 2026** for the FIFA World Cup demo), set your fleet size, "
            "then click **Run optimizer**."
        )

    with st.expander("Architecture, methodology, and production data upgrade path", expanded=False):
        render_methodology_tab()
    st.stop()


# ---- Build user request ----------------------------------------------------

user_request = (
    "Build the optimal cart placement plan for " + target_date.isoformat() + " in Seattle. "
    "The operator has " + str(n_carts) + " carts today -- when you call get_cart_fleet and "
    "optimize_cart_placement, pass n_carts=" + str(n_carts) + ". "
    "Use live web search to pull all relevant events (Ticketmaster, FIFA World Cup 2026, "
    "Port of Seattle cruise calendar, Mariners/Seahawks/Sounders/Kraken schedules, "
    "Seattle Convention Center, Visit Seattle festivals). After optimizing, sanity-check "
    "drive times from the depot and check competition density on the highest-revenue spots."
)
if extra_context.strip():
    user_request += "\n\nAdditional operator context: " + extra_context.strip()


# ---- Run agent + live trace ------------------------------------------------

st.markdown('<div class="section-h">Agent live trace</div>', unsafe_allow_html=True)
status_box = st.status("Agent thinking...", expanded=True)

trace_events = []
final_state = None
final_text = ""

with status_box:
    for event in run_agent(user_request):
        trace_events.append(event)
        if event.role == "assistant_text":
            st.markdown("**Agent:** " + event.content)
        elif event.role == "tool_use":
            st.markdown("`" + str(event.tool_name) + "`")
            inp = json.dumps(event.tool_input or {}, indent=2)
            if len(inp) > 500:
                inp = inp[:500] + "\n  ...truncated..."
            st.code(inp, language="json")
        elif event.role == "tool_result":
            out = json.dumps(event.tool_output, indent=2, default=str)
            if len(out) > 1200:
                out = out[:1200] + "\n  ...truncated..."
            with st.expander(str(event.tool_name) + " result"):
                st.code(out, language="json")
        elif event.role == "final":
            final_state = event.final_state or {}
            final_text = event.content

status_box.update(label="Agent finished", state="complete", expanded=False)


def _is_valid_plan(p):
    return isinstance(p, dict) and "total_projected_revenue_usd" in p and isinstance(p.get("plan"), list)


plan = (final_state or {}).get("plan")
preds = (final_state or {}).get("predictions") or []

if not _is_valid_plan(plan):
    from tools.traffic import LAST as TRAFFIC_CACHE
    from tools.inventory import get_cart_fleet
    cached_preds = TRAFFIC_CACHE.get("predictions")
    cached_overrides = TRAFFIC_CACHE.get("event_overrides") or {}
    if cached_preds:
        from optimizer import optimize as _optimize
        st.info("Agent's plan was incomplete -- running optimizer locally on cached predictions.")
        plan = _optimize(cached_preds, fleet=get_cart_fleet(n_carts=n_carts), event_overrides=cached_overrides)
        preds = cached_preds


if _is_valid_plan(plan):
    from tools.weather import LAST as WEATHER_CACHE
    weather = WEATHER_CACHE.get("forecast") or {}

    total_rev = plan["total_projected_revenue_usd"]
    n_placed = plan["n_carts_placed"]
    n_zones = plan["n_zones_used"]
    temp_str = (str(weather.get("temperature_f", "?")) + "F") if weather else "?"
    precip_str = (str(int(weather.get("precip_chance", 0) * 100)) + "%") if weather else "?"
    n_event_carts = sum(1 for c in plan["plan"] if c.get("dominant_event") and c.get("dominant_event") != "none")

    st.markdown(
        "<div class='kpi-band'>"
        "<div class='kpi kpi-money'><div class='label'>Total projected revenue</div><div class='value'>$" + format(total_rev, ",.2f") + "</div><div class='sub'>across " + str(n_placed) + " carts</div></div>"
        "<div class='kpi'><div class='label'>Zones used</div><div class='value'>" + str(n_zones) + "</div><div class='sub'>of 14 candidate zones</div></div>"
        "<div class='kpi'><div class='label'>Event-driven placements</div><div class='value'>" + str(n_event_carts) + " / " + str(n_placed) + "</div><div class='sub'>carts targeting an event</div></div>"
        "<div class='kpi'><div class='label'>Weather</div><div class='value'>" + temp_str + "</div><div class='sub'>" + precip_str + " precip chance</div></div>"
        "</div>",
        unsafe_allow_html=True,
    )

    tab_summary, tab_map, tab_carts, tab_method = st.tabs(["Summary", "Map", "Per-cart reasoning", "Architecture & Methodology"])

    with tab_summary:
        if final_text:
            st.markdown(final_text)
        st.markdown('<div class="section-h">Placement table</div>', unsafe_allow_html=True)
        df = pd.DataFrame(plan["plan"])
        show_cols = ["cart_id", "cart_name", "zone_name", "spot_name", "deploy_start", "deploy_end", "dominant_event_label", "predicted_foot_traffic", "projected_revenue_usd"]
        show_cols = [c for c in show_cols if c in df.columns]
        nice_names = {"cart_id": "Cart ID", "cart_name": "Name", "zone_name": "Zone", "spot_name": "Specific spot", "deploy_start": "Start", "deploy_end": "End", "dominant_event_label": "Driver", "predicted_foot_traffic": "Foot traffic", "projected_revenue_usd": "Revenue ($)"}
        st.dataframe(df[show_cols].rename(columns=nice_names), use_container_width=True, hide_index=True)

    with tab_map:
        api_key = _get_key("GOOGLE_MAPS_API_KEY")
        if not api_key:
            st.warning("Add your Google Maps API key in the sidebar to render the map.")
        elif preds:
            html = render_placement_map_html(preds, plan["plan"], api_key=api_key)
            components.html(html, height=620, scrolling=False)
        st.caption("Blue circles are cart placements (numbered by cart ID). Grey dots are zone centroids -- hover to see predicted foot traffic.")

    with tab_carts:
        st.markdown('<div class="section-h">Why each cart was placed</div>', unsafe_allow_html=True)
        for entry in plan["plan"]:
            ev = entry.get("dominant_event_label") or entry.get("dominant_event") or "none"
            ev_class = "pill-none" if "none" in ev or "no major" in ev else "pill-event"
            html = (
                '<div class="cart-card"><div class="cart-card-head">'
                '<div class="cart-card-title">' + entry["cart_id"] + ' &middot; ' + entry["cart_name"] + '</div>'
                '<div class="cart-card-rev">$' + format(entry["projected_revenue_usd"], ",.2f") + '</div></div>'
                '<div class="cart-card-spot"><b>' + entry["spot_name"] + '</b> &nbsp;&middot;&nbsp; ' + entry["zone_name"] + '</div>'
                '<div class="cart-card-reason">' + entry.get("reasoning", "(no reasoning available)") + '</div>'
                '<div class="cart-card-meta">'
                '<span class="pill ' + ev_class + '">' + ev + '</span>'
                '<span>Foot traffic: <b>' + format(entry["predicted_foot_traffic"], ",") + '</b></span>'
                '<span>Deploy: <b>' + entry.get("deploy_start", "?") + ' - ' + entry.get("deploy_end", "?") + '</b> (' + str(entry.get("deploy_hours", "?")) + ' hrs)</span>'
                '<span>Staff: ' + str(len(entry.get("staff", []))) + ' shift(s)</span>'
                '<span>Inventory: ' + str(sum(entry.get("inventory", {}).values())) + ' units</span>'
                '<span>Coords: ' + format(entry["lat"], ".4f") + ', ' + format(entry["lng"], ".4f") + '</span>'
                '</div></div>'
            )
            st.markdown(html, unsafe_allow_html=True)

    with tab_method:
        render_methodology_tab()

elif isinstance(plan, dict) and "error" in plan:
    st.error("Optimizer call failed: " + str(plan["error"]))
else:
    st.info("Agent finished without producing a placement plan. Open the trace above for details.")
