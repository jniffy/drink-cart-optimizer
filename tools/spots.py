"""Pick the best intra-zone micro-spot for a cart given the dominant event."""
from __future__ import annotations
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
_spots: dict | None = None


def _load() -> dict:
    global _spots
    if _spots is None:
        raw = json.loads((DATA_DIR / "zone_spots.json").read_text())
        _spots = {k: v for k, v in raw.items() if not k.startswith("_")}
    return _spots


def list_zone_spots(zone_id: str) -> list[dict]:
    return _load().get(zone_id, [])


def pick_best_spot(zone_id: str, event_type: str = "none",
                   exclude_names: set[str] | None = None) -> dict | None:
    """
    Choose the highest-affinity intra-zone spot for the given dominant event.
    `exclude_names` lets the optimizer avoid placing two carts at the same
    micro-spot when stacking multiple carts in one zone.
    """
    exclude_names = exclude_names or set()
    candidates = [s for s in list_zone_spots(zone_id) if s["name"] not in exclude_names]
    if not candidates:
        return None
    def score(s):
        a = s.get("event_affinity", {})
        # Fall back to "none" affinity if the specific event type isn't listed.
        return a.get(event_type, a.get("none", 1.0))
    candidates.sort(key=score, reverse=True)
    best = candidates[0]
    return {
        "name": best["name"],
        "lat": best["lat"],
        "lng": best["lng"],
        "event_type": event_type,
        "affinity_score": score(best),
    }
