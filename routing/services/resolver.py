"""Resolve a start/finish string to (lat, lon). Reuses the Phase 1 city table."""
import re
import csv
from functools import lru_cache
import numpy as np
from config import settings


class LocationError(Exception):
    pass


@lru_cache(maxsize=1)
def _city_lookup():
    """All US cities from the bundled census file, keyed CITY|ST. Zero network."""
    d = {}
    with open(settings.US_CITIES_CSV, newline="") as f:
        for row in csv.DictReader(f):
            key = _norm(row["CITY"]) + "|" + row["STATE_CODE"].strip().upper()
            d.setdefault(key, (float(row["LATITUDE"]), float(row["LONGITUDE"])))
    return d

def _norm(s):
    s = re.sub(r"[^A-Z0-9 ]", " ", str(s).upper().strip())
    s = re.sub(r"\s+", " ", s).strip()
    return re.sub(r"^(ST|SAINT)\b", "ST", s)


def resolve(text):
    """'41.88,-87.63' -> parse. 'Chicago, IL' -> city table. Returns (lat, lon)."""
    text = text.strip()

    # Tier 1: raw "lat,lon"
    m = re.match(r"^\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*$", text)
    if m:
        lat, lon = float(m.group(1)), float(m.group(2))
        if 24 <= lat <= 50 and -125 <= lon <= -66:
            return lat, lon
        raise LocationError(f"Coordinates outside the continental US: {text}")

    # Tier 2: "City, ST" against the bundled table (zero network)
    if "," in text:
        city, state = text.rsplit(",", 1)
        key = _norm(city) + "|" + state.strip().upper()
        hit = _city_lookup().get(key)
        if hit:
            return hit

    raise LocationError(f"Could not resolve '{text}'. Use 'City, ST' or 'lat,lon'.")