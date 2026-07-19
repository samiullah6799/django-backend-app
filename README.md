# Fuel Route Optimizer

A Django REST API that finds the most cost-effective fueling plan for a road
trip between two US locations. Given a 500-mile vehicle range and per-gallon
prices for ~6,600 truck stops, it returns the optimal set of fuel stops, the
total fuel cost, and a map of the route.

---

## Quick start

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py load_fuel_prices      # clean + load 6,626 stations
python manage.py build_index           # attach coordinates (offline)
python manage.py runserver
```

**API:**
