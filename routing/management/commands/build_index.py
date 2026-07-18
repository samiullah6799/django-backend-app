import re
import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from routing.models import FuelStation


OVERRIDES = {
    "PORT WENTWORTH|GA":  (32.16451, -81.18009),
    "ELIZABETHPORT|NJ":   (40.66300, -74.21400),
    "EVERGREEN|AL":       (31.42667, -86.98944),
    "HENRICO|VA":         (37.53880, -77.42480),
    "UNIVERSITY PARK|IL": (41.43944, -87.69722),
}


def norm_city(s):
    s = re.sub(r"[^A-Z0-9 ]", " ", str(s).upper().strip())
    s = re.sub(r"\s+", " ", s).strip()
    return re.sub(r"^(ST|SAINT)\b", "ST", s)


class Command(BaseCommand):
    help = "Attach coordinates to every FuelStation."

    @transaction.atomic
    def handle(self, *args, **opts):
        cities = pd.read_csv(settings.US_CITIES_CSV)
        cities["key"] = cities["CITY"].map(norm_city) + "|" + cities["STATE_CODE"]
        lut_df = cities.groupby("key")[["LATITUDE", "LONGITUDE"]].mean()
        lut = {k: (row.LATITUDE, row.LONGITUDE) for k, row in lut_df.iterrows()}

        spaceless = {}
        for k in lut:
            city, st = k.rsplit("|", 1)
            spaceless[city.replace(" ", "") + "|" + st] = k

        stations = list(FuelStation.objects.all())
        counts = {"city_centroid": 0, "spaceless": 0, "manual_override": 0, "MISSING": 0}

        for s in stations:
            key = norm_city(s.city) + "|" + s.state
            space_key = key.rsplit("|", 1)[0].replace(" ", "") + "|" + s.state

            if key in lut:
                s.lat, s.lon = lut[key]
                s.coord_source = "city_centroid"
                counts["city_centroid"] += 1
            elif space_key in spaceless:
                s.lat, s.lon = lut[spaceless[space_key]]
                s.coord_source = "spaceless"
                counts["spaceless"] += 1
            elif key in OVERRIDES:
                s.lat, s.lon = OVERRIDES[key]
                s.coord_source = "manual_override"
                counts["manual_override"] += 1
            else:
                counts["MISSING"] += 1
                self.stdout.write(self.style.WARNING(f"NO MATCH: {key}"))

        FuelStation.objects.bulk_update(
            stations, ["lat", "lon", "coord_source"], batch_size=1000
        )

        nulls = FuelStation.objects.filter(lat__isnull=True).count()
        assert nulls == 0, f"{nulls} stations still have no coordinates"
        self.stdout.write(self.style.SUCCESS(f"geocoded: {counts}"))