"""Orchestrate the full plan: resolve -> route -> corridor -> optimize. Cached."""
import time
from django.conf import settings
from django.core.cache import cache
from routing.services.resolver import resolve
from routing.services.osrm import fetch_route
from routing.services.corridor import match_corridor
from routing.services.optimizer import plan_fuel_stops


def plan(start_text, finish_text):
    key = f"route:{start_text.strip().lower()}|{finish_text.strip().lower()}"
    cached = cache.get(key)
    if cached:
        cached["meta"]["cached"] = True
        cached["meta"]["external_api_calls"] = 0
        return cached

    t0 = time.perf_counter()
    start = resolve(start_text)
    finish = resolve(finish_text)

    route = fetch_route(start, finish)                     # the ONE API call
    stations, details = match_corridor(
        route,
        tolerance_miles=settings.CORRIDOR_TOLERANCE_MILES,
        spacing_miles=settings.ROUTE_SAMPLE_SPACING_MILES,
    )
    stops, total = plan_fuel_stops(
        stations, route.distance_miles,
        tank_gallons=settings.TANK_GALLONS,
        mpg=settings.MILES_PER_GALLON,
        start_tank=settings.START_TANK_GALLONS,
    )

    consumed = route.distance_miles / settings.MILES_PER_GALLON
    purchased = sum(s["gallons"] for s in stops)

    result = {
        "route": {
            "distance_miles": round(route.distance_miles, 1),
            "geometry": route.points[:, [1, 0]].tolist(),   # [lon,lat] for Leaflet
        },
        "stops": stops,
        "fuel": {
            "gallons_consumed": round(consumed, 2),
            "gallons_purchased": round(purchased, 2),
            "total_cost_usd": total,
        },
        "assumptions": {
            "range_miles": settings.VEHICLE_RANGE_MILES,
            "mpg": settings.MILES_PER_GALLON,
            "tank_gallons": settings.TANK_GALLONS,
            "start_tank": "full",
            "price_rule": "median",
            "corridor_miles": settings.CORRIDOR_TOLERANCE_MILES,
            "coordinates": "city_centroid",
        },
        "meta": {
            "external_api_calls": 1,
            "cached": False,
            "compute_ms": round((time.perf_counter() - t0) * 1000, 1),
        },
    }
    cache.set(key, result, timeout=3600)
    return result