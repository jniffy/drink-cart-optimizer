"""Cart placement optimizer tool — wraps optimizer.optimize."""
from __future__ import annotations

from optimizer import optimize
from .inventory import get_cart_fleet
from .traffic import LAST as TRAFFIC_CACHE


def optimize_cart_placement(predictions=None, event_overrides=None, n_carts=None):
    if not predictions:
        predictions = TRAFFIC_CACHE.get("predictions")
        if not predictions:
            return {"error": "no predictions available -- call predict_foot_traffic first"}

    if not event_overrides:
        event_overrides = TRAFFIC_CACHE.get("event_overrides") or {}

    fleet = get_cart_fleet(n_carts=n_carts) if n_carts else None
    return optimize(predictions, fleet=fleet, event_overrides=event_overrides)
