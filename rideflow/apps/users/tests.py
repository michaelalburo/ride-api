from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


class UserManagerTests(TestCase):
    def test_create_superuser_defaults_role_to_admin(self):
        user = User.objects.create_superuser(email='root@test.com', password='pass12345')
        self.assertEqual(user.role, User.Role.ADMIN)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)


class UserAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email='admin@test.com', password='pass12345', role=User.Role.ADMIN,
        )
        self.rider = User.objects.create_user(
            email='rider@test.com', password='pass12345', role=User.Role.RIDER,
        )

    def test_unauthenticated_request_is_rejected(self):
        response = self.client.get('/api/users/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_admin_request_is_forbidden(self):
        self.client.force_authenticate(user=self.rider)
        response = self.client.get('/api/users/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_list_users(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_user_hashes_password_and_never_returns_it(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post('/api/users/', {
            'email': 'newrider@test.com', 'role': 'rider', 'password': 'secretpass1',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn('password', response.data)
        created = User.objects.get(email='newrider@test.com')
        self.assertTrue(created.check_password('secretpass1'))
