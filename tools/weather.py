"""Free Open-Meteo weather forecast -- no API key required.

Caches the most recent forecast at module level so the Streamlit UI can
display the same weather the agent used.
"""
from __future__ import annotations
import datetime as dt
import requests

SEATTLE = (47.6062, -122.3321)
LAST: dict = {"date": None, "forecast": None}


def get_weather_forecast(date: str) -> dict:
    target = dt.date.fromisoformat(date)
    lat, lng = SEATTLE
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lng}"
        "&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max"
        f"&temperature_unit=fahrenheit&timezone=America/Los_Angeles"
        f"&start_date={date}&end_date={date}"
    )
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()["daily"]
        tmax = data["temperature_2m_max"][0]
        tmin = data["temperature_2m_min"][0]
        precip = data["precipitation_probability_max"][0]
        out = {
            "date": date,
            "temperature_f": round((tmax + tmin) / 2, 1),
            "high_f": tmax,
            "low_f": tmin,
            "precip_chance": round((precip or 0) / 100, 2),
            "source": "Open-Meteo",
        }
    except Exception as e:
        month = target.month
        if month in (6, 7, 8):
            t, p = 72.0, 0.10
        elif month in (12, 1, 2):
            t, p = 43.0, 0.55
        else:
            t, p = 56.0, 0.35
        out = {
            "date": date,
            "temperature_f": t,
            "high_f": t + 6,
            "low_f": t - 6,
            "precip_chance": p,
            "source": f"seasonal_average (Open-Meteo failed: {e})",
        }
    LAST["date"] = date
    LAST["forecast"] = out
    return out
