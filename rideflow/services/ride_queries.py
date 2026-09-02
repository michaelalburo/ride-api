from datetime import timedelta

from django.db.models import Prefetch
from django.utils import timezone

from rideflow.apps.rides.models import Ride, RideEvent
from rideflow.utils.geo import distance_expression

ORDERING_FIELDS = {'pickup_time', '-pickup_time', 'distance', '-distance'}


class RideQueryService:
    @staticmethod
    def list_queryset(ordering='pickup_time', latitude=None, longitude=None):
        cutoff = timezone.now() - timedelta(hours=24)

        queryset = Ride.objects.select_related('rider', 'driver').prefetch_related(
            Prefetch(
                'ride_events',
                queryset=RideEvent.objects.filter(created_at__gte=cutoff),
                to_attr='todays_ride_events',
            ),
        )

        if ordering in ('distance', '-distance'):
            queryset = queryset.annotate(distance=distance_expression(latitude, longitude))

        return queryset.order_by(ordering)
