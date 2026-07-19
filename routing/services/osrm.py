"""The single external call: coordinates in, route geometry + distance out."""
from dataclasses import dataclass
import requests
import numpy as np
from django.conf import settings


class RouteError(Exception):
    pass


@dataclass
class Route:
    points: np.ndarray        # shape (N, 2): [lat, lon] per vertex
    distance_miles: float


def fetch_route(start, end, timeout=15):
    """start, end: (lat, lon). Returns a Route. Raises RouteError on failure."""
    # OSRM wants lon,lat order — the classic gotcha
    coords = f"{start[1]},{start[0]};{end[1]},{end[0]}"
    url = f"{settings.OSRM_BASE_URL}/route/v1/driving/{coords}"
    params = {"overview": "full", "geometries": "geojson"}

    try:
        resp = requests.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        raise RouteError(f"OSRM request failed: {e}") from e

    if data.get("code") != "Ok" or not data.get("routes"):
        raise RouteError(f"OSRM returned: {data.get('code', 'no response')}")

    route = data["routes"][0]
    # GeoJSON coordinates are [lon, lat] — flip to [lat, lon] for our geo.py
    lonlat = np.array(route["geometry"]["coordinates"], dtype=float)
    latlon = lonlat[:, [1, 0]]
    return Route(points=latlon, distance_miles=route["distance"] / 1609.344)