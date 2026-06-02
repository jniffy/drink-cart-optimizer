"""Google Places API (New) wrapper — nearby competition + place details."""
from __future__ import annotations
import os
import requests

NEARBY_URL = "https://places.googleapis.com/v1/places:searchNearby"

# Place types that compete with a drink cart
COMPETITION_TYPES = ["cafe", "coffee_shop", "bakery", "restaurant", "bar"]


def find_nearby_competition(lat: float, lng: float,
                            radius_m: int = 300,
                            included_types: list[str] | None = None) -> dict:
    """Count and summarize nearby drink/food businesses around a candidate spot."""
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return {"error": "GOOGLE_MAPS_API_KEY not set"}

    types = included_types or COMPETITION_TYPES
    body = {
        "includedTypes": types,
        "maxResultCount": 20,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": float(radius_m),
            }
        },
    }
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.primaryType,places.rating,places.userRatingCount,places.priceLevel,places.location",
    }
    try:
        r = requests.post(NEARBY_URL, json=body, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
        places = data.get("places", [])
        summary = []
        rating_total = 0.0
        rating_n = 0
        for p in places:
            name = (p.get("displayName") or {}).get("text", "?")
            rating = p.get("rating")
            count = p.get("userRatingCount")
            if rating:
                rating_total += rating
                rating_n += 1
            summary.append({
                "name": name,
                "type": p.get("primaryType"),
                "rating": rating,
                "user_rating_count": count,
                "price_level": p.get("priceLevel"),
            })
        return {
            "lat": lat,
            "lng": lng,
            "radius_m": radius_m,
            "n_competitors": len(places),
            "avg_competitor_rating": round(rating_total / rating_n, 2) if rating_n else None,
            "competitors": summary,
            "saturation_warning": (
                "high competition density — consider a different spot or a differentiated drink mix"
                if len(places) >= 8 else None
            ),
        }
    except requests.HTTPError as e:
        return {"error": f"Places API error: {e.response.status_code} {e.response.text[:200]}"}
    except Exception as e:
        return {"error": f"Places API exception: {e}"}
