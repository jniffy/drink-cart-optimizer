"""
Trains and serves the foot-traffic linear regression model.

Training data sources (combined when both present):
  1. data/historical_real.csv  — REAL hourly pedestrian/cycle counts pulled
     from data.seattle.gov by data/fetch_sdot.py, daily-aggregated and joined
     with historical Seattle weather from Open-Meteo.  Anchors the no-event
     baseline to actual observed traffic.
  2. data/historical_events.csv — synthetic but plausible event-day rows so
     the regression learns the lift from concerts, stadium games, the World
     Cup, conventions, cruise ship calls, etc.  Real SDOT counters don't
     tell us *which day* had which event, so we have to teach event lift
     synthetically.

Model:  sklearn LinearRegression on
    day_of_week, is_weekend, month, is_summer,
    temperature_f, precip_chance,
    base_foot_traffic, event_draw
"""
from __future__ import annotations
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score

DATA_DIR = Path(__file__).parent / "data"
SYNTHETIC = DATA_DIR / "historical_events.csv"
REAL = DATA_DIR / "historical_real.csv"
ZONES = DATA_DIR / "seattle_zones.json"

EVENT_DRAW = {
    "none": 0,
    "music_venue": 800,
    "theater": 1500,
    "convention": 2500,
    "arena": 5500,
    "festival": 7000,
    "stadium": 9000,
    "cruise": 4500,
    "world_cup": 18000,
}

FEATURES = [
    "day_of_week", "is_weekend", "month", "is_summer",
    "temperature_f", "precip_chance",
    "base_foot_traffic", "event_draw",
]


def _prep(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["event_draw"] = df["nearby_event_type"].map(EVENT_DRAW).fillna(0)
    return df


def _load_history() -> tuple[pd.DataFrame, dict]:
    sources = {}
    frames = []
    if REAL.exists():
        real = _prep(pd.read_csv(REAL))
        frames.append(real)
        sources["real_sdot_rows"] = int(len(real))
    if SYNTHETIC.exists():
        synth = _prep(pd.read_csv(SYNTHETIC))
        frames.append(synth)
        sources["synthetic_event_rows"] = int(len(synth))
    if not frames:
        raise FileNotFoundError("no training data found")
    return pd.concat(frames, ignore_index=True), sources


def train():
    df, sources = _load_history()
    X = df[FEATURES].values
    y = df["foot_traffic"].values
    model = LinearRegression().fit(X, y)
    preds = model.predict(X)
    metrics = {
        "n_train": int(len(df)),
        "sources": sources,
        "mae": float(mean_absolute_error(y, preds)),
        "r2": float(r2_score(y, preds)),
        "coefficients": dict(zip(FEATURES, [float(c) for c in model.coef_])),
        "intercept": float(model.intercept_),
    }
    return model, metrics


_MODEL = None
_METRICS = None
_ZONES = None


def get_model():
    global _MODEL, _METRICS
    if _MODEL is None:
        _MODEL, _METRICS = train()
    return _MODEL, _METRICS


def get_zones():
    global _ZONES
    if _ZONES is None:
        _ZONES = json.loads(ZONES.read_text())["zones"]
    return _ZONES


def predict_zone_day(
    zone_id, day_of_week, month, temperature_f, precip_chance,
    nearby_event_type="none",
):
    """Single-zone prediction the agent can call as a tool."""
    model, _ = get_model()
    zones = {z["id"]: z for z in get_zones()}
    if zone_id not in zones:
        raise ValueError("unknown zone " + repr(zone_id))
    z = zones[zone_id]
    row = np.array([[
        day_of_week,
        1 if day_of_week >= 5 else 0,
        month,
        1 if month in (6, 7, 8) else 0,
        temperature_f,
        precip_chance,
        z["base_foot_traffic"],
        EVENT_DRAW.get(nearby_event_type, 0),
    ]])
    pred = float(model.predict(row)[0])
    return {
        "zone_id": zone_id,
        "zone_name": z["name"],
        "lat": z["lat"],
        "lng": z["lng"],
        "predicted_foot_traffic": max(0, int(pred)),
    }


def predict_all_zones(
    day_of_week, month, temperature_f, precip_chance, event_overrides=None,
):
    event_overrides = event_overrides or {}
    out = []
    for z in get_zones():
        out.append(predict_zone_day(
            z["id"],
            day_of_week=day_of_week,
            month=month,
            temperature_f=temperature_f,
            precip_chance=precip_chance,
            nearby_event_type=event_overrides.get(z["id"], "none"),
        ))
    return out


if __name__ == "__main__":
    _, metrics = get_model()
    print(json.dumps(metrics, indent=2))
