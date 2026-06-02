"""Google Routes API wrapper — drive/transit/walk time between two points."""
from __future__ import annotations
import os
import requests

ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"

MODE_MAP = {
    "driving": "DRIVE",
    "drive": "DRIVE",
    "walking": "WALK",
    "walk": "WALK",
    "bicycling": "BICYCLE",
    "bike": "BICYCLE",
    "transit": "TRANSIT",
}


def get_route_time(origin_lat: float, origin_lng: float,
                   destination_lat: float, destination_lng: float,
                   mode: str = "driving",
                   departure_time_iso: str | None = None) -> dict:
    """Compute travel time + distance between two lat/lng points.

    Returns:
        duration_seconds, duration_minutes, distance_meters, distance_miles, mode
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return {"error": "GOOGLE_MAPS_API_KEY not set"}

    travel_mode = MODE_MAP.get(mode.lower(), "DRIVE")
    body = {
        "origin": {"location": {"latLng": {"latitude": origin_lat, "longitude": origin_lng}}},
        "destination": {"location": {"latLng": {"latitude": destination_lat, "longitude": destination_lng}}},
        "travelMode": travel_mode,
    }
    if travel_mode == "DRIVE":
        body["routingPreference"] = "TRAFFIC_AWARE"
    if departure_time_iso and travel_mode in ("DRIVE", "TRANSIT"):
        body["departureTime"] = departure_time_iso

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "routes.duration,routes.distanceMeters",
    }
    try:
        r = requests.post(ROUTES_URL, json=body, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
        if not data.get("routes"):
            return {"error": "no route found", "raw": data}
        route = data["routes"][0]
        # duration is "1234s"
        dur_s = int(str(route["duration"]).rstrip("s"))
        dist_m = int(route["distanceMeters"])
        return {
            "duration_seconds": dur_s,
            "duration_minutes": round(dur_s / 60, 1),
            "distance_meters": dist_m,
            "distance_miles": round(dist_m / 1609.34, 2),
            "mode": travel_mode,
        }
    except requests.HTTPError as e:
        return {"error": f"Routes API error: {e.response.status_code} {e.response.text[:200]}"}
    except Exception as e:
        return {"error": f"Routes API exception: {e}"}
