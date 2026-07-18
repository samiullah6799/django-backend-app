"""Distance math for route/corridor work. Pure functions, no Django."""
import numpy as np

EARTH_RADIUS_MILES = 3958.8


def haversine_miles(lat1, lon1, lat2, lon2):
    """Great-circle distance in miles. Works on scalars or numpy arrays."""
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_MILES * np.arcsin(np.sqrt(a))


def cumulative_miles(points):
    """points: array of (lat, lon). Returns running mile-marker per vertex, starting at 0."""
    points = np.asarray(points, dtype=float)
    seg = haversine_miles(points[:-1, 0], points[:-1, 1],
                          points[1:, 0], points[1:, 1])
    return np.concatenate([[0.0], np.cumsum(seg)])