"""Match fuel stations to a route corridor, producing (mile, price) pairs."""
from functools import lru_cache
import numpy as np
from routing.services.geo import haversine_miles, cumulative_miles


@lru_cache(maxsize=1)
def _station_array():
    """Load all stations once: array of (lat, lon, price) + name/city lists."""
    from routing.models import FuelStation
    rows = list(FuelStation.objects.values_list("lat", "lon", "price", "name", "city", "state"))
    coords = np.array([(r[0], r[1], float(r[2])) for r in rows])
    meta = [(r[3], f"{r[4]}, {r[5]}") for r in rows]
    return coords, meta


def match_corridor(route, tolerance_miles=20, spacing_miles=10):
    """
    route: Route from osrm.fetch_route (has .points [lat,lon], .distance_miles)
    Returns (stations_for_optimizer, details) where
      stations_for_optimizer = sorted list of (mile_marker, price)
      details = parallel list of dicts with name/city for the response
    """
    coords, meta = _station_array()
    S_lat, S_lon, S_price = coords[:, 0], coords[:, 1], coords[:, 2]

    pts = route.points
    cum = cumulative_miles(pts)                      # mile-marker per vertex

    # subsample to ~spacing_miles
    marks = np.arange(0, route.distance_miles, spacing_miles)
    idx = np.searchsorted(cum, marks)
    idx = np.clip(idx, 0, len(pts) - 1)
    Q = pts[idx]                                     # query points
    Qcum = cum[idx]                                  # their mile-markers

    # bounding-box prefilter (cheap) before the real distance test
    pad = (tolerance_miles + spacing_miles) / 60.0   # deg per ~mile, rough
    m = ((S_lat >= Q[:, 0].min() - pad) & (S_lat <= Q[:, 0].max() + pad) &
         (S_lon >= Q[:, 1].min() - pad) & (S_lon <= Q[:, 1].max() + pad))
    cand = np.flatnonzero(m)
    if len(cand) == 0:
        return [], []

    # distance from each candidate to every query point; keep the nearest
    radius = tolerance_miles + spacing_miles / 2      # see note below
    d = haversine_miles(S_lat[cand][:, None], S_lon[cand][:, None],
                        Q[None, :, 0], Q[None, :, 1])
    nearest = d.argmin(axis=1)
    nearest_d = d[np.arange(len(cand)), nearest]
    hit = nearest_d <= radius

    sel = cand[hit]
    mile = Qcum[nearest[hit]]
    order = np.argsort(mile)
    sel, mile = sel[order], mile[order]

    stations = [(float(mile[i]), float(S_price[sel[i]])) for i in range(len(sel))]
    details = [{"mile": float(mile[i]), "price": float(S_price[sel[i]]),
                "name": meta[sel[i]][0], "location": meta[sel[i]][1]}
               for i in range(len(sel))]
    return stations, details