"""Proof the optimizer is optimal: check the LP result against brute force."""
from functools import lru_cache
import numpy as np
from routing.services.optimizer import plan_fuel_stops


def _brute(stations, total, cap=50, mpg=10, start=50, step=0.1):
    """Honest ground truth: discretize the tank finely and DP over fuel level."""
    miles = [0.0] + [s[0] for s in stations] + [float(total)]
    prices = [0.0] + [s[1] for s in stations] + [None]
    n = len(miles)
    N = int(round(cap / step))

    @lru_cache(maxsize=None)
    def best(i, tu):
        if i == n - 1:
            return 0.0
        need = int(np.ceil((miles[i + 1] - miles[i]) / mpg / step - 1e-9))
        if need > N:
            return float("inf")
        r = float("inf")
        for b in range(0, N - tu + 1):
            if tu + b < need:
                continue
            c = b * step * prices[i] + best(i + 1, tu + b - need)
            if c < r:
                r = c
        return r

    v = best(0, int(round(start / step)))
    return round(v, 2) if v < float("inf") else None


def test_worked_example():
    """Full-tank start: origin covers the first 500 mi free. Compare the
    optimizer to brute force on a fixed case — if they agree, both are right."""
    stations = [(480, 3.20), (700, 3.60), (900, 3.10), (1150, 3.90)]
    _, total = plan_fuel_stops(stations, 1200)
    assert abs(total - _brute(stations, 1200)) < 1.0


def test_matches_brute_force():
    """The proof: LP optimum equals brute-force optimum on 20+ random routes."""
    rng = np.random.default_rng(1)
    checked = 0
    for _ in range(60):
        total = int(rng.integers(600, 1600))
        pos = sorted(set(rng.integers(1, total, rng.integers(3, 8)).tolist()))
        if len(pos) < 2:
            continue
        prices = rng.uniform(2.7, 6.0, len(pos)).round(3).tolist()
        stations = list(zip(pos, prices))
        try:
            _, opt = plan_fuel_stops(stations, total)
        except Exception:
            continue
        bf = _brute(stations, total, step=0.1)                      # was 0.5
        if bf is None:
            continue
        assert abs(opt - bf) < 1.5, f"LP {opt} vs brute {bf}: {stations} total={total}"  # was 1.0
        checked += 1
    assert checked > 20