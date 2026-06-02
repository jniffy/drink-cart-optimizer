"""
Constrained non-linear cart placement optimizer.

Two-stage:
  1. ZONE assignment: enumerate feasible cart->zone assignments and score each
     via a non-linear objective (revenue with cannibalization penalty).
  2. Per-cart INTRA-ZONE micro-spot pick + DEPLOYMENT SCHEDULE: anchor each
     cart's deploy hours to the dominant event's start time, clipped to the
     cart's operating_window and capped by max_hours.
"""
from __future__ import annotations
import itertools
import json
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

EVENT_LABELS = {
    "world_cup":  "FIFA World Cup 2026 match",
    "stadium":    "stadium event (Mariners/Seahawks/Sounders)",
    "arena":      "arena event (Kraken/Storm/concert)",
    "theater":    "theater performance",
    "music_venue":"live music show",
    "convention": "convention center event",
    "festival":   "street festival / fan zone",
    "cruise":     "cruise ship call (Pier 66/91)",
    "none":       "no major event (baseline foot traffic)",
}

# When does the dominant event "happen"? Used to anchor cart deploy windows.
EVENT_PEAK_HOUR = {
    "world_cup":  18,   # WC matches are evening
    "stadium":    18,   # baseball/soccer evenings
    "arena":      19,   # arena shows + games
    "theater":    19,   # curtain
    "music_venue":20,
    "convention": 11,   # convention foot traffic peaks midday
    "festival":   13,   # festivals run afternoon
    "cruise":     12,   # cruise pax disembark late morning / midday
    "none":       11,   # default to lunch peak
}


def load_fleet():
    return json.loads((DATA_DIR / "carts.json").read_text())


def _cart_revenue(cart, zone_pred):
    foot = zone_pred["predicted_foot_traffic"]
    capacity_day = cart["capacity_per_hour"] * cart["max_hours"]
    converted = min(capacity_day, 0.03 * foot)
    return converted * cart["avg_ticket_usd"]


def _objective(assignment, carts, preds, max_per_zone):
    revenue = 0.0
    counts = {}
    for cart_idx, zone_idx in enumerate(assignment):
        counts[zone_idx] = counts.get(zone_idx, 0) + 1
        nth = counts[zone_idx]
        scale = 1.0 if nth == 1 else 0.55  # cannibalization (non-linear)
        revenue += scale * _cart_revenue(carts[cart_idx], preds[zone_idx])
    penalty = sum(10_000 * (c - max_per_zone)
                  for c in counts.values() if c > max_per_zone)
    return -(revenue - penalty)


def _build_schedule(cart, ev_type):
    """Return (start_HH:MM, end_HH:MM, hours) clipped to the cart's operating
    window and centered around the event's peak hour."""
    win_start = datetime.strptime(cart["operating_window"][0], "%H:%M")
    win_end = datetime.strptime(cart["operating_window"][1], "%H:%M")
    max_hrs = cart["max_hours"]

    peak = EVENT_PEAK_HOUR.get(ev_type, 11)
    # Aim to be at the cart from 3 hours before to 2 hours after the event peak
    aim_start = datetime.strptime(f"{max(0, peak-3):02d}:00", "%H:%M")
    aim_end = datetime.strptime(f"{min(23, peak+2):02d}:00", "%H:%M")

    start = max(win_start, aim_start)
    end = min(win_end, aim_end)

    if end <= start:                # event is outside the operating window
        start = win_start
        end = win_end

    # Cap by max_hours (anchor on event peak side)
    span = (end - start).total_seconds() / 3600.0
    if span > max_hrs:
        # If event is in the evening, push start later; if morning, push end earlier
        if peak >= 15:
            start = end - timedelta(hours=max_hrs)
        else:
            end = start + timedelta(hours=max_hrs)
        span = (end - start).total_seconds() / 3600.0

    return start.strftime("%H:%M"), end.strftime("%H:%M"), round(span, 1)


def _build_reasoning(cart, zone_pred, ev_type, nth_in_zone, scale, rev,
                      start_time, end_time, span_hrs):
    foot = zone_pred["predicted_foot_traffic"]
    capacity_day = cart["capacity_per_hour"] * cart["max_hours"]
    converted = min(capacity_day, 0.03 * foot)
    cap_limited = capacity_day < 0.03 * foot
    driver = EVENT_LABELS.get(ev_type, ev_type)
    parts = [
        f"**{zone_pred['zone_name']}** is predicted to draw ~{foot:,} pedestrians today, driven by: {driver}.",
        f"Deploy {start_time} -> {end_time} ({span_hrs} hrs), anchored on the event's typical peak hour and clipped to this cart's operating window.",
    ]
    if nth_in_zone > 1:
        parts.append(
            f"This is the **{nth_in_zone}nd cart** in this zone, so its sales are "
            f"discounted {int((1-scale)*100)}% to account for cannibalization."
        )
    if cap_limited:
        parts.append(
            f"Revenue is **capacity-limited**: {cart['capacity_per_hour']}/hr x {cart['max_hours']} hrs = "
            f"{capacity_day} drinks max, below the 3% conversion of foot traffic ({int(0.03*foot):,} potential customers)."
        )
    else:
        parts.append(
            f"Revenue is **demand-limited**: ~3% of {foot:,} pedestrians = {int(converted)} drinks expected, "
            f"below this cart's daily capacity of {capacity_day}."
        )
    parts.append(
        f"Projected revenue = {int(converted * scale)} drinks x ${cart['avg_ticket_usd']:.2f} avg ticket = **${rev:,.2f}**."
    )
    return " ".join(parts)


def optimize(predictions, fleet=None, event_overrides=None):
    fleet = fleet or load_fleet()
    event_overrides = event_overrides or {}
    carts = fleet["carts"]
    max_per_zone = fleet["constraints"]["max_carts_per_zone"]

    n_carts = len(carts)
    n_zones = len(predictions)

    if n_zones == 0:
        return {"error": "predictions list is empty -- call predict_foot_traffic first"}
    required_keys = {"zone_id", "zone_name", "lat", "lng", "predicted_foot_traffic"}
    bad = [i for i, p in enumerate(predictions)
           if not isinstance(p, dict) or not required_keys.issubset(p.keys())]
    if bad:
        return {"error": f"prediction entries missing required keys {sorted(required_keys)}; bad indices: {bad[:3]}"}

    # Stage 1: zone-level assignment
    best_assignment = None
    best_neg = float("inf")
    for assignment in itertools.product(range(n_zones), repeat=n_carts):
        counts = {}
        ok = True
        for zi in assignment:
            counts[zi] = counts.get(zi, 0) + 1
            if counts[zi] > max_per_zone:
                ok = False
                break
        if not ok:
            continue
        score = _objective(list(assignment), carts, predictions, max_per_zone)
        if score < best_neg:
            best_neg = score
            best_assignment = assignment

    if best_assignment is None:
        return {"error": "no feasible cart-to-zone assignment found"}

    # Stage 2: intra-zone refinement + schedule + reasoning
    from tools.spots import pick_best_spot

    used_spots_per_zone = {}
    plan = []
    counts = {}
    for cart_idx, zone_idx in enumerate(best_assignment):
        zone_pred = predictions[zone_idx]
        zid = zone_pred["zone_id"]
        counts[zid] = counts.get(zid, 0) + 1
        nth = counts[zid]
        scale = 1.0 if nth == 1 else 0.55
        rev = scale * _cart_revenue(carts[cart_idx], zone_pred)

        ev_type = event_overrides.get(zid, "none")
        used = used_spots_per_zone.setdefault(zid, set())
        spot = pick_best_spot(zid, ev_type, exclude_names=used)
        if spot:
            used.add(spot["name"])
            spot_name = spot["name"]
            lat, lng = spot["lat"], spot["lng"]
        else:
            spot_name = zone_pred["zone_name"] + " (centroid)"
            lat, lng = zone_pred["lat"], zone_pred["lng"]

        # Deployment schedule (start/end time)
        start_time, end_time, span_hrs = _build_schedule(carts[cart_idx], ev_type)

        reasoning = _build_reasoning(
            carts[cart_idx], zone_pred, ev_type, nth, scale, rev,
            start_time, end_time, span_hrs,
        )

        plan.append({
            "cart_id": carts[cart_idx]["id"],
            "cart_name": carts[cart_idx]["name"],
            "zone_id": zid,
            "zone_name": zone_pred["zone_name"],
            "spot_name": spot_name,
            "lat": lat, "lng": lng,
            "predicted_foot_traffic": zone_pred["predicted_foot_traffic"],
            "dominant_event": ev_type,
            "dominant_event_label": EVENT_LABELS.get(ev_type, ev_type),
            "projected_revenue_usd": round(rev, 2),
            "deploy_start": start_time,
            "deploy_end": end_time,
            "deploy_hours": span_hrs,
            "staff": carts[cart_idx].get("staff", []),
            "inventory": carts[cart_idx].get("inventory", {}),
            "reasoning": reasoning,
        })

    total = round(sum(p["projected_revenue_usd"] for p in plan), 2)
    return {
        "plan": plan,
        "total_projected_revenue_usd": total,
        "n_carts_placed": len(plan),
        "n_zones_used": len(set(p["zone_id"] for p in plan)),
    }
