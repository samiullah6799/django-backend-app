from decimal import Decimal
import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from routing.models import FuelStation

CANADA = {"AB", "BC", "MB", "NB", "NS", "ON", "QC", "SK", "YT"}


class Command(BaseCommand):
    help = "Load and clean fuel prices into FuelStation."

    @transaction.atomic
    def handle(self, *args, **opts):
        # --- your proven REPL transform, rungs 1-5 ---
        df = pd.read_csv(settings.FUEL_PRICES_CSV)
        df = df.rename(columns={
            "OPIS Truckstop ID": "opis_id",
            "Truckstop Name": "name",
            "Address": "address",
            "City": "city",
            "State": "state",
            "Retail Price": "price",
        }).drop(columns=["Rack ID"])

        for c in ["name", "address", "city", "state"]:
            df[c] = df[c].str.strip()

        df = df[~df.state.isin(CANADA)].copy()

        g = df.groupby("opis_id").agg(
            name=("name", lambda s: max(sorted(set(s)), key=len)),
            address=("address", "first"),
            city=("city", "first"),
            state=("state", "first"),
            price=("price", "median"),
        ).reset_index()
        g["price"] = g["price"].round(3)

        # --- write to DB (new: the REPL never did this) ---
        FuelStation.objects.all().delete()
        FuelStation.objects.bulk_create([
            FuelStation(
                opis_id=int(row["opis_id"]),
                name=row["name"],
                address=row["address"],
                city=row["city"],
                state=row["state"],
                price=Decimal(str(row["price"])),
            )
            for row in g.to_dict("records")
        ], batch_size=1000)

        n = FuelStation.objects.count()
        assert n == 6626, f"expected 6626, got {n}"
        self.stdout.write(self.style.SUCCESS(f"loaded {n} stations"))