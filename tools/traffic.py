"""Foot-traffic prediction tool — wraps model.predict_all_zones.

Stores the latest predictions in a module-level cache so other tools
(notably optimize_cart_placement) can use them without forcing the LLM
to round-trip a large JSON array.
"""
from __future__ import annotations
import datetime as dt

from model import predict_all_zones, get_model

# Cache of the most recent predict_foot_traffic call so optimize_cart_placement
# doesn't require the LLM to reproduce the entire predictions array.
LAST: dict = {
    "predictions": None,
    "event_overrides": None,
    "date": None,
}


def predict_foot_traffic(date, temperature_f, precip_chance, event_overrides=None):
    """Predict foot-traffic across all Seattle zones for a given date.

    event_overrides:
        {"sodo": "stadium", "seattle_center": "arena", "downtown": "cruise"}
        Allowed values: none, music_venue, theater, convention, arena, festival,
        stadium, cruise, world_cup.
    """
    target = dt.date.fromisoformat(date)
    overrides = event_overrides or {}
    preds = predict_all_zones(
        day_of_week=target.weekday(),
        month=target.month,
        temperature_f=temperature_f,
        precip_chance=precip_chance,
        event_overrides=overrides,
    )
    LAST["predictions"] = preds
    LAST["event_overrides"] = overrides
    LAST["date"] = date

    _, metrics = get_model()
    return {
        "date": date,
        "predictions": preds,
        "model_diagnostics": {
            "type": "LinearRegression",
            "training_rows": metrics["n_train"],
            "training_r2": round(metrics["r2"], 3),
            "training_mae": round(metrics["mae"], 1),
        },
    }
