from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from rideflow.apps.users.models import User
from rideflow.apps.users.serializers import UserSerializer

from .models import Ride, RideEvent


class RideEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = RideEvent
        fields = ['id', 'ride', 'description', 'created_at']


class RideSerializer(serializers.ModelSerializer):
    id_rider = UserSerializer(source='rider', read_only=True)
    id_driver = UserSerializer(source='driver', read_only=True)
    rider = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), write_only=True)
    driver = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), write_only=True)
    todays_ride_events = serializers.SerializerMethodField()

    class Meta:
        model = Ride
        fields = [
            'id', 'status', 'id_rider', 'id_driver', 'rider', 'driver',
            'pickup_latitude', 'pickup_longitude',
            'dropoff_latitude', 'dropoff_longitude',
            'pickup_time', 'todays_ride_events',
        ]

    def get_todays_ride_events(self, obj):
        events = getattr(obj, 'todays_ride_events', None)
        if events is None:
            cutoff = timezone.now() - timedelta(hours=24)
            events = obj.ride_events.filter(created_at__gte=cutoff)
        return RideEventSerializer(events, many=True).data
