"""Agent tools — each function returns a JSON-serializable dict (or HTML for mapping)."""
from .weather import get_weather_forecast
from .geocoding import geocode_venue
from .inventory import get_cart_fleet, get_seattle_zones
from .traffic import predict_foot_traffic
from .placement import optimize_cart_placement
from .mapping import render_placement_map_html
from .spots import list_zone_spots, pick_best_spot
from .routes import get_route_time
from .places import find_nearby_competition

__all__ = [
    "get_weather_forecast",
    "geocode_venue",
    "get_cart_fleet",
    "get_seattle_zones",
    "predict_foot_traffic",
    "optimize_cart_placement",
    "render_placement_map_html",
    "list_zone_spots",
    "pick_best_spot",
    "get_route_time",
    "find_nearby_competition",
]
