"""The fuel-cost optimizer. Pure logic — no Django, no geo, no network.

Total gallons burned is fixed (miles / mpg). We only choose WHICH prices
we pay. Greedy rules: buy just enough to reach anything cheaper ahead;
otherwise fill up and drive to the cheapest station in range.
"""

import numpy as np
from scipy.optimize import linprog


class InfeasibleRoute(Exception):
    pass


def plan_fuel_stops(stations, total_miles, tank_gallons=50, mpg=10, start_tank=50):
    """
    stations: list of (mile_marker, price), sorted by mile_marker, all < total_miles.
    Returns (stops, total_cost). Raises InfeasibleRoute if a gap exceeds range.
    Exact optimum via linear programming.
    """
    # feasibility: no gap between consecutive points may exceed range
    range_miles = tank_gallons * mpg
    pts = [0.0] + [s[0] for s in stations] + [float(total_miles)]
    for a, b in zip(pts, pts[1:]):
        if b - a > range_miles + 1e-9:
            raise InfeasibleRoute(f"{b - a:.0f} mi gap exceeds {range_miles:.0f} mi range")

    miles = np.array([0.0] + [float(s[0]) for s in stations])
    prices = np.array([0.0] + [float(s[1]) for s in stations])
    n = len(miles)
    consumed = miles / mpg

    # buy[j] = gallons purchased at node j (buy[0] = 0, origin starts full)
    L_lt = np.zeros((n, n))   # sum over k < j
    L_le = np.zeros((n, n))   # sum over k <= j
    for j in range(n):
        for k in range(1, j):
            L_lt[j, k] = 1.0
        for k in range(1, j + 1):
            L_le[j, k] = 1.0

    A = np.vstack([-L_lt, L_le, -np.ones((1, n))])
    b = np.concatenate([
        start_tank - consumed,                       # arrival fuel >= 0
        tank_gallons - start_tank + consumed,        # tank after buying <= capacity
        [start_tank - total_miles / mpg],            # must reach destination
    ])
    res = linprog(prices, A_ub=A, b_ub=b,
                  bounds=[(0, 0)] + [(0, None)] * (n - 1), method="highs")
    if not res.success:
        raise InfeasibleRoute("no feasible fueling plan")

    stops = []
    for j in range(1, n):
        buy = res.x[j]
        if buy > 1e-6:
            stops.append({"mile": miles[j], "price": prices[j],
                          "gallons": round(buy, 3), "cost": round(buy * prices[j], 2)})
    return stops, round(float(res.fun), 2)

    """
    stations: list of (mile_marker, price), sorted by mile_marker, all < total_miles.
    Returns (stops, total_cost) where stops is a list of dicts.
    """
    range_miles = tank_gallons * mpg

    # origin = a virtual station at mile 0, price 0, with the starting tank
    miles = [0.0] + [s[0] for s in stations]
    prices = [0.0] + [s[1] for s in stations]
    n = len(miles)

    tank = start_tank        # gallons in tank on arrival at current node
    i = 0                    # current node index
    stops = []
    total_cost = 0.0

    while True:
        here_mile, here_price = miles[i], prices[i]

        # can we reach the destination from here?
        if total_miles - here_mile <= range_miles:
            need = (total_miles - here_mile) / mpg
            buy = max(0.0, need - tank)
            if buy > 1e-9:
                total_cost += buy * here_price
                stops.append({"mile": here_mile, "price": here_price,
                              "gallons": buy, "cost": buy * here_price})
            break

        # stations reachable from here (ahead, within range)
        reachable = [j for j in range(i + 1, n) if miles[j] - here_mile <= range_miles]
        if not reachable:
            raise InfeasibleRoute(
                f"No station within {range_miles} mi after mile {here_mile:.0f}"
            )

        # first cheaper station ahead?
        cheaper = [j for j in reachable if prices[j] < here_price]
        if cheaper:
            j = cheaper[0]
            need = (miles[j] - here_mile) / mpg
            buy = max(0.0, need - tank)
            if buy > 1e-9:
                total_cost += buy * here_price
                stops.append({"mile": here_mile, "price": here_price,
                              "gallons": buy, "cost": buy * here_price})
            tank = tank + buy - need
        else:
            # nothing cheaper ahead — fill up, go to cheapest reachable
            buy = tank_gallons - tank
            if buy > 1e-9:
                total_cost += buy * here_price
                stops.append({"mile": here_mile, "price": here_price,
                              "gallons": buy, "cost": buy * here_price})
            tank = tank_gallons
            j = min(reachable, key=lambda k: prices[k])
            tank -= (miles[j] - here_mile) / mpg

        i = j

    return stops, round(total_cost, 2)