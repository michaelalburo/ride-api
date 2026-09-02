from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from .models import Ride, RideEvent

User = get_user_model()


class RideListAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email='admin@test.com', password='pass12345', role=User.Role.ADMIN,
        )
        self.rider1 = User.objects.create_user(
            email='rider1@test.com', password='pass12345', role=User.Role.RIDER,
        )
        self.rider2 = User.objects.create_user(
            email='rider2@test.com', password='pass12345', role=User.Role.RIDER,
        )
        self.driver = User.objects.create_user(
            email='driver1@test.com', password='pass12345', role=User.Role.DRIVER,
        )

        now = timezone.now()
        # Manila
        self.ride1 = Ride.objects.create(
            status=Ride.Status.EN_ROUTE, rider=self.rider1, driver=self.driver,
            pickup_latitude=14.5995, pickup_longitude=120.9842,
            dropoff_latitude=14.6091, dropoff_longitude=121.0223,
            pickup_time=now - timedelta(hours=2),
        )
        # Cebu, ~570km from Manila
        self.ride2 = Ride.objects.create(
            status=Ride.Status.PICKUP, rider=self.rider2, driver=self.driver,
            pickup_latitude=10.3157, pickup_longitude=123.8854,
            dropoff_latitude=10.3, dropoff_longitude=123.9,
            pickup_time=now - timedelta(hours=1),
        )
        RideEvent.objects.create(
            ride=self.ride1, description='Status changed to pickup',
            created_at=now - timedelta(hours=1),
        )
        RideEvent.objects.create(
            ride=self.ride1, description='Old event outside 24h',
            created_at=now - timedelta(hours=25),
        )
        RideEvent.objects.create(
            ride=self.ride2, description='Status changed to pickup',
            created_at=now - timedelta(minutes=30),
        )

        self.client.force_authenticate(user=self.admin)

    def test_unauthenticated_request_is_rejected(self):
        client = APIClient()
        response = client.get('/api/rides/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_admin_request_is_forbidden(self):
        client = APIClient()
        client.force_authenticate(user=self.rider1)
        response = client.get('/api/rides/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_includes_nested_rider_and_driver(self):
        response = self.client.get('/api/rides/')
        ride_data = next(r for r in response.data['results'] if r['id'] == self.ride1.id)
        self.assertEqual(ride_data['id_rider']['email'], self.rider1.email)
        self.assertEqual(ride_data['id_driver']['email'], self.driver.email)

    def test_todays_ride_events_excludes_events_older_than_24h(self):
        response = self.client.get('/api/rides/')
        ride_data = next(r for r in response.data['results'] if r['id'] == self.ride1.id)
        descriptions = [e['description'] for e in ride_data['todays_ride_events']]
        self.assertEqual(descriptions, ['Status changed to pickup'])

    def test_filter_by_status(self):
        response = self.client.get('/api/rides/', {'status': Ride.Status.PICKUP})
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.ride2.id)

    def test_filter_by_rider_email(self):
        response = self.client.get('/api/rides/', {'rider_email': self.rider2.email})
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.ride2.id)

    def test_ordering_by_pickup_time(self):
        response = self.client.get('/api/rides/', {'ordering': 'pickup_time'})
        ids = [r['id'] for r in response.data['results']]
        self.assertEqual(ids, [self.ride1.id, self.ride2.id])

    def test_ordering_by_pickup_time_descending(self):
        response = self.client.get('/api/rides/', {'ordering': '-pickup_time'})
        ids = [r['id'] for r in response.data['results']]
        self.assertEqual(ids, [self.ride2.id, self.ride1.id])

    def test_ordering_by_distance(self):
        response = self.client.get(
            '/api/rides/', {'ordering': 'distance', 'lat': 14.5995, 'lng': 120.9842},
        )
        ids = [r['id'] for r in response.data['results']]
        self.assertEqual(ids, [self.ride1.id, self.ride2.id])

    def test_distance_ordering_requires_coordinates(self):
        response = self.client.get('/api/rides/', {'ordering': 'distance'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_ordering_value_rejected(self):
        response = self.client.get('/api/rides/', {'ordering': 'bogus'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pagination_page_size(self):
        response = self.client.get('/api/rides/', {'page_size': 1})
        self.assertEqual(len(response.data['results']), 1)
        self.assertIsNotNone(response.data['next'])

    def test_list_query_count(self):
        with self.assertNumQueries(3):
            response = self.client.get('/api/rides/')
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_distance_ordering_query_count(self):
        with self.assertNumQueries(3):
            response = self.client.get(
                '/api/rides/', {'ordering': 'distance', 'lat': 14.5995, 'lng': 120.9842},
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
