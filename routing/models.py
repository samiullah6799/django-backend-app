from django.db import models

class FuelStation(models.Model):
    opis_id = models.IntegerField(unique=True, db_index=True)
    name    = models.CharField(max_length=100)
    address = models.CharField(max_length=150, blank=True)
    city    = models.CharField(max_length=64)
    state   = models.CharField(max_length=2, db_index=True)
    price   = models.DecimalField(max_digits=6, decimal_places=3)  # $/gallon
    lat     = models.FloatField(null=True, blank=True)
    lon     = models.FloatField(null=True, blank=True)
    coord_source = models.CharField(max_length=24, blank=True)

    class Meta:
        ordering = ["opis_id"]
