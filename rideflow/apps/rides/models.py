from django.conf import settings
from django.db import models
from django.utils import timezone


class Ride(models.Model):
    class Status(models.TextChoices):
        EN_ROUTE = 'en-route', 'En route'
        PICKUP = 'pickup', 'Pickup'
        DROPOFF = 'dropoff', 'Dropoff'

    status = models.CharField(max_length=20, choices=Status.choices, db_index=True)
    rider = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rides_as_rider',
    )
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rides_as_driver',
    )
    pickup_latitude = models.FloatField()
    pickup_longitude = models.FloatField()
    dropoff_latitude = models.FloatField()
    dropoff_longitude = models.FloatField()
    pickup_time = models.DateTimeField(db_index=True)

    def __str__(self):
        return f'Ride #{self.pk} ({self.status})'


class RideEvent(models.Model):
    ride = models.ForeignKey(Ride, on_delete=models.CASCADE, related_name='ride_events')
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['ride', 'created_at']),
        ]
        ordering = ['created_at']

    def __str__(self):
        return f'{self.description} @ {self.created_at}'
