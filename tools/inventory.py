"""RAG-style retrieval over local operator data (cart fleet, zone catalog).

The fleet supports a dynamic n_carts override so the agent (and the UI)
can simulate operators with different fleet sizes without editing carts.json.
"""
from __future__ import annotations
import copy
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def _load_fleet():
    return json.loads((DATA_DIR / "carts.json").read_text())


def get_cart_fleet(n_carts=None):
    """Return the operator's cart inventory + placement constraints + depot.

    n_carts: optional override of the fleet size. If larger than the base
        catalog, additional carts are synthesized by cycling through the
        templates' specs. Names are reset to "Cart N" for clarity.
    """
    fleet = _load_fleet()
    base = fleet["carts"]
    if n_carts is None or n_carts == len(base):
        return fleet

    n_carts = max(1, int(n_carts))
    new_carts = []
    for i in range(n_carts):
        template = copy.deepcopy(base[i % len(base)])
        template["id"] = f"EC-{i+1:02d}"
        template["name"] = f"Cart {i+1}"
        new_carts.append(template)
    fleet = copy.deepcopy(fleet)
    fleet["carts"] = new_carts
    fleet["fleet_size_override"] = n_carts
    return fleet


def get_seattle_zones():
    """Return the catalog of candidate placement zones with major venues."""
    return json.loads((DATA_DIR / "seattle_zones.json").read_text())
