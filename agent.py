"""OpenAI orchestrator for the Drink Cart Placement Optimizer.

Resilience features:
  - On RateLimitError: exponential backoff + auto-fallback to gpt-4o-mini.
  - Tool-call deduplication: re-calling the same tool with same args returns
    cached result with a "move on" hint.
  - Event-overrides validation: if predict_foot_traffic is called with empty
    event_overrides but venues were geocoded earlier, the dispatcher returns
    a structured warning prompting the agent to retry with proper overrides.
"""
from __future__ import annotations
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Iterator

from openai import OpenAI, RateLimitError

import tools as agent_tools

DEFAULT_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
FALLBACK_MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = """You are the planning agent for **Emerald City Carts**, a Seattle mobile drink-cart operator (depot in Georgetown). Produce a revenue-maximizing cart placement plan for a single target date.

EFFICIENT LOOP -- follow exactly. Do NOT repeat tools or re-search topics already covered.

1. **ONE web_search** for "Seattle events <date> sports concerts cruise festivals". Read all results from that single call. If you genuinely need more, do at MOST 2 additional searches for specific gaps. Do NOT do 5+ web searches.

2. **Extract & Parse**: tag each event with one of (world_cup, stadium, arena, theater, music_venue, convention, festival, cruise, none) AND note its expected audience demographics (e.g. "Mariners game: family + 20-50 male-skewed", "World Cup: international + adult", "Bumbershoot: 18-35 broad", "cruise call: 50+ tourists"). Carry these demographic notes into your final summary so the operator knows which drink mix to favor (cold + alcoholic for stadium, hot + espresso for cruise mornings, etc.). Geocode unfamiliar venues with `geocode_venue`.

3. `get_weather_forecast` (one call).

4. `get_cart_fleet` with n_carts if user specified a fleet size.

5. **predict_foot_traffic** -- THIS STEP IS CRITICAL. You MUST pass `event_overrides` mapping zone_id -> event_type for EVERY zone where step 1 found an event. If you skip event_overrides, the regression returns flat baseline traffic and the entire optimization is wrong.

   WORKED EXAMPLE: if web_search found a Mariners game at T-Mobile Park, a Demi Lovato concert at Climate Pledge Arena, and a Norwegian Joy cruise at Pier 66, you geocoded them and got zones {sodo, seattle_center, belltown}. You MUST then call:

       predict_foot_traffic(
         date="2026-05-13",
         temperature_f=72.0,
         precip_chance=0.1,
         event_overrides={
           "sodo": "stadium",
           "seattle_center": "arena",
           "belltown": "cruise"
         }
       )

   If two events fall in the same zone, pick the highest-impact tag (priority: world_cup > stadium > arena > festival > convention > theater > music_venue > cruise).

   If web_search found events in venues you couldn't geocode to one of our 14 zones, just skip those events.

6. `optimize_cart_placement` with no arguments (it reuses cached predictions). Pass n_carts only if user specified a fleet size.

7. (Optional) for the top 1-2 highest-revenue spots, call get_route_time + find_nearby_competition. Skip if near token budget.

8. Final summary: events, cart-by-cart placement, total revenue, top risks.

CRITICAL: do not call the same tool twice with the same arguments. Be concise.
"""


def _custom_tool(name, description, params):
    return {"type": "function", "name": name, "description": description, "parameters": params}


TOOL_SCHEMAS = [
    {"type": "web_search_preview"},
    _custom_tool(
        "get_weather_forecast",
        "Get daily weather for Seattle for a specific date.",
        {"type": "object", "properties": {"date": {"type": "string"}},
         "required": ["date"], "additionalProperties": False},
    ),
    _custom_tool(
        "geocode_venue",
        "Look up a Seattle venue by name; returns lat/lng + nearest placement zone_id. Call this for every event venue you find via web_search so you know which zone each event maps to.",
        {"type": "object", "properties": {"venue_name": {"type": "string"}},
         "required": ["venue_name"], "additionalProperties": False},
    ),
    _custom_tool(
        "get_cart_fleet",
        "Retrieve cart inventory + depot. Pass n_carts to override base 6-cart fleet.",
        {"type": "object",
         "properties": {"n_carts": {"type": "integer"}},
         "additionalProperties": False},
    ),
    _custom_tool(
        "get_seattle_zones",
        "Catalog of placement zones + major venues.",
        {"type": "object", "properties": {}, "additionalProperties": False},
    ),
    _custom_tool(
        "predict_foot_traffic",
        "Run regression across all Seattle zones. event_overrides maps zone_id -> event_type and is REQUIRED whenever web_search found events. Allowed event types: none, music_venue, theater, convention, arena, festival, stadium, cruise, world_cup. Without event_overrides, the model returns flat baseline traffic and the optimizer cannot account for events.",
        {"type": "object",
         "properties": {
             "date": {"type": "string"},
             "temperature_f": {"type": "number"},
             "precip_chance": {"type": "number"},
             "event_overrides": {"type": "object", "additionalProperties": {"type": "string"}},
         },
         "required": ["date", "temperature_f", "precip_chance"],
         "additionalProperties": False},
    ),
    _custom_tool(
        "optimize_cart_placement",
        "Run the constrained non-linear optimizer (zone assignment with cannibalization penalty + intra-zone spot picker + deployment-window scheduler). Reuses cached predictions/event_overrides automatically. Pass n_carts if user specified a fleet size.",
        {"type": "object",
         "properties": {
             "event_overrides": {"type": "object", "additionalProperties": {"type": "string"}},
             "n_carts": {"type": "integer"},
         },
         "required": [], "additionalProperties": False},
    ),
    _custom_tool(
        "list_zone_spots",
        "Inspect intra-zone micro-spots in a single zone.",
        {"type": "object", "properties": {"zone_id": {"type": "string"}},
         "required": ["zone_id"], "additionalProperties": False},
    ),
    _custom_tool(
        "get_route_time",
        "Google Routes API drive/walk/transit time + distance.",
        {"type": "object",
         "properties": {
             "origin_lat": {"type": "number"},
             "origin_lng": {"type": "number"},
             "destination_lat": {"type": "number"},
             "destination_lng": {"type": "number"},
             "mode": {"type": "string"},
         },
         "required": ["origin_lat", "origin_lng", "destination_lat", "destination_lng"],
         "additionalProperties": False},
    ),
    _custom_tool(
        "find_nearby_competition",
        "Google Places API. Cafes/restaurants/bars within radius_m of a point.",
        {"type": "object",
         "properties": {
             "lat": {"type": "number"},
             "lng": {"type": "number"},
             "radius_m": {"type": "number"},
         },
         "required": ["lat", "lng"], "additionalProperties": False},
    ),
]


# Track venues geocoded during this session so we can sanity-check
# event_overrides on subsequent predict_foot_traffic calls.
_GEOCODED_ZONES: set[str] = set()


def _dispatch(name, args):
    if name == "get_weather_forecast":
        return agent_tools.get_weather_forecast(args["date"])
    if name == "geocode_venue":
        result = agent_tools.geocode_venue(args["venue_name"])
        if isinstance(result, dict) and result.get("zone_id"):
            _GEOCODED_ZONES.add(result["zone_id"])
        return result
    if name == "get_cart_fleet":
        return agent_tools.get_cart_fleet(n_carts=args.get("n_carts"))
    if name == "get_seattle_zones":
        return agent_tools.get_seattle_zones()
    if name == "predict_foot_traffic":
        overrides = args.get("event_overrides") or {}
        # If we previously geocoded venues but the model is calling predict
        # with no event_overrides, return a warning so it retries instead
        # of getting silently flat baseline predictions.
        if _GEOCODED_ZONES and not overrides:
            return {
                "error": "missing_event_overrides",
                "message": (
                    "You called predict_foot_traffic with empty event_overrides, "
                    "but you previously geocoded venues to these zones: "
                    + ", ".join(sorted(_GEOCODED_ZONES))
                    + ". You MUST tag each of those zones with the appropriate event_type "
                    "(world_cup, stadium, arena, theater, music_venue, convention, festival, cruise) "
                    "and re-call predict_foot_traffic with event_overrides set. "
                    "Without this the regression returns flat baseline traffic and the optimization is wrong."
                ),
                "geocoded_zones": sorted(_GEOCODED_ZONES),
                "allowed_event_types": ["world_cup", "stadium", "arena", "theater",
                                          "music_venue", "convention", "festival", "cruise"],
            }
        return agent_tools.predict_foot_traffic(
            date=args["date"],
            temperature_f=args["temperature_f"],
            precip_chance=args["precip_chance"],
            event_overrides=overrides,
        )
    if name == "optimize_cart_placement":
        return agent_tools.optimize_cart_placement(
            predictions=args.get("predictions"),
            event_overrides=args.get("event_overrides"),
            n_carts=args.get("n_carts"),
        )
    if name == "list_zone_spots":
        return {"zone_id": args["zone_id"],
                "spots": agent_tools.list_zone_spots(args["zone_id"])}
    if name == "get_route_time":
        return agent_tools.get_route_time(
            origin_lat=args["origin_lat"], origin_lng=args["origin_lng"],
            destination_lat=args["destination_lat"], destination_lng=args["destination_lng"],
            mode=args.get("mode", "driving"),
        )
    if name == "find_nearby_competition":
        return agent_tools.find_nearby_competition(
            lat=args["lat"], lng=args["lng"],
            radius_m=int(args.get("radius_m") or 300),
        )
    raise ValueError(f"unknown tool: {name}")


@dataclass
class Trace:
    role: str
    content: str = ""
    tool_name: str | None = None
    tool_input: dict | None = None
    tool_output: Any = None
    final_state: dict | None = None


def _signature(name, args):
    return name + "::" + json.dumps(args or {}, sort_keys=True)


def _call_with_retry_and_fallback(client, model_state, **kwargs):
    delays = [3, 8, 20]
    for attempt, delay in enumerate(delays + [None]):
        try:
            kwargs["model"] = model_state["model"]
            return client.responses.create(**kwargs)
        except RateLimitError:
            if attempt == 1 and model_state["model"] != FALLBACK_MODEL:
                model_state["model"] = FALLBACK_MODEL
                model_state["fell_back"] = True
                continue
            if delay is None:
                raise
            time.sleep(delay)


def run_agent(user_request, max_turns=20):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        yield Trace(role="final", content="ERROR: OPENAI_API_KEY not set")
        return
    client = OpenAI(api_key=api_key)

    # Reset per-session state
    _GEOCODED_ZONES.clear()

    model_state = {"model": DEFAULT_MODEL, "fell_back": False}
    input_items = [{"role": "user", "content": user_request}]
    last_predictions = None
    last_plan = None
    call_cache: dict[str, Any] = {}

    for _turn in range(max_turns):
        try:
            response = _call_with_retry_and_fallback(
                client, model_state,
                instructions=SYSTEM_PROMPT,
                tools=TOOL_SCHEMAS,
                input=input_items,
            )
        except RateLimitError as e:
            yield Trace(role="final",
                        content="OpenAI rate limit hit even after fallback. Wait 1-2 minutes and retry. " + str(e),
                        final_state={"predictions": last_predictions, "plan": last_plan})
            return

        if model_state.get("fell_back"):
            yield Trace(role="assistant_text",
                        content="(switched to gpt-4o-mini due to rate limits on the original model)")
            model_state["fell_back"] = False

        for item in response.output:
            t = getattr(item, "type", None)
            if t == "message":
                for blk in getattr(item, "content", []) or []:
                    text = getattr(blk, "text", None)
                    if text and text.strip():
                        yield Trace(role="assistant_text", content=text)
            elif t == "web_search_call":
                yield Trace(role="tool_use", tool_name="web_search",
                            tool_input={"status": getattr(item, "status", "")})

        input_items.extend([
            it.model_dump() if hasattr(it, "model_dump") else it
            for it in response.output
        ])

        function_calls = [it for it in response.output
                          if getattr(it, "type", None) == "function_call"]
        if not function_calls:
            final_text = ""
            for item in response.output:
                if getattr(item, "type", None) == "message":
                    for blk in getattr(item, "content", []) or []:
                        text = getattr(blk, "text", None)
                        if text:
                            final_text += text
            yield Trace(role="final", content=final_text,
                        final_state={"predictions": last_predictions, "plan": last_plan})
            return

        for fc in function_calls:
            name = fc.name
            try:
                args = json.loads(fc.arguments or "{}")
            except json.JSONDecodeError:
                args = {}

            sig = _signature(name, args)
            if sig in call_cache:
                output = {
                    "note": "duplicate call detected; reusing prior result -- please move to the next step",
                    "previous_result": call_cache[sig],
                }
            else:
                try:
                    output = _dispatch(name, args)
                except Exception as e:
                    output = {"error": str(e)}
                call_cache[sig] = output

            if name == "predict_foot_traffic" and isinstance(output, dict) and output.get("predictions"):
                last_predictions = output.get("predictions")
            if name == "optimize_cart_placement" and isinstance(output, dict) and "total_projected_revenue_usd" in output:
                last_plan = output

            yield Trace(role="tool_use", tool_name=name, tool_input=args)
            yield Trace(role="tool_result", tool_name=name, tool_output=output)

            input_items.append({
                "type": "function_call_output",
                "call_id": fc.call_id,
                "output": json.dumps(output, default=str),
            })

    yield Trace(role="final", content="(max turns exceeded)",
                final_state={"predictions": last_predictions, "plan": last_plan})
