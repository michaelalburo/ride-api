from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError

from rideflow.services.ride_queries import ORDERING_FIELDS, RideQueryService

from .filters import RideFilter
from .models import Ride, RideEvent
from .serializers import RideEventSerializer, RideSerializer


class RideViewSet(viewsets.ModelViewSet):
    serializer_class = RideSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = RideFilter

    def get_queryset(self):
        if self.action != 'list':
            return Ride.objects.select_related('rider', 'driver').all()

        ordering = self.request.query_params.get('ordering', 'pickup_time')
        if ordering not in ORDERING_FIELDS:
            raise ValidationError({'ordering': f'Must be one of {sorted(ORDERING_FIELDS)}.'})

        latitude = longitude = None
        if ordering in ('distance', '-distance'):
            latitude = self._parse_coordinate('lat')
            longitude = self._parse_coordinate('lng')

        return RideQueryService.list_queryset(ordering=ordering, latitude=latitude, longitude=longitude)

    def _parse_coordinate(self, param):
        value = self.request.query_params.get(param)
        if value is None:
            raise ValidationError({param: 'Required when ordering by distance.'})
        try:
            return float(value)
        except ValueError:
            raise ValidationError({param: 'Must be a number.'})


class RideEventViewSet(viewsets.ModelViewSet):
    queryset = RideEvent.objects.select_related('ride').all()
    serializer_class = RideEventSerializer
