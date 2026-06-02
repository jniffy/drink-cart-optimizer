"""Google Maps Geocoding wrapper. Falls back to a known-venue dictionary when no key."""
from __future__ import annotations
import json
import os
from pathlib import Path

import googlemaps

DATA_DIR = Path(__file__).parent.parent / "data"
_zones_cache: dict | None = None


def _load_known_venues() -> dict[str, dict]:
    global _zones_cache
    if _zones_cache is None:
        _zones_cache = json.loads((DATA_DIR / "seattle_zones.json").read_text())
    out: dict[str, dict] = {}
    for v in _zones_cache["major_venues"]:
        zone = next(z for z in _zones_cache["zones"] if z["id"] == v["zone"])
        out[v["name"].lower()] = {
            "name": v["name"],
            "lat": zone["lat"],
            "lng": zone["lng"],
            "zone_id": v["zone"],
            "zone_name": zone["name"],
        }
    return out


def _nearest_zone(lat: float, lng: float) -> dict:
    zones = json.loads((DATA_DIR / "seattle_zones.json").read_text())["zones"]
    best = min(zones, key=lambda z: (z["lat"] - lat) ** 2 + (z["lng"] - lng) ** 2)
    return best


def geocode_venue(venue_name: str) -> dict:
    """Return lat/lng + nearest Seattle zone for a venue name."""
    known = _load_known_venues()
    if venue_name.lower() in known:
        return {**known[venue_name.lower()], "source": "known_venue_table"}

    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return {
            "venue_name": venue_name,
            "error": "GOOGLE_MAPS_API_KEY not set and venue not in known table",
            "source": "none",
        }
    try:
        client = googlemaps.Client(key=api_key)
        results = client.geocode(f"{venue_name}, Seattle, WA")
        if not results:
            return {"venue_name": venue_name, "error": "no results", "source": "google_maps"}
        loc = results[0]["geometry"]["location"]
        zone = _nearest_zone(loc["lat"], loc["lng"])
        return {
            "name": venue_name,
            "formatted_address": results[0]["formatted_address"],
            "lat": loc["lat"],
            "lng": loc["lng"],
            "zone_id": zone["id"],
            "zone_name": zone["name"],
            "source": "google_maps",
        }
    except Exception as e:
        return {"venue_name": venue_name, "error": str(e), "source": "google_maps_error"}
