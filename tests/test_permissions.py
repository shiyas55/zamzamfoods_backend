from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from apps.accounts.models import User
from apps.routes.models import Route

class RolePermissionsTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="test_owner", password="password", role=User.Role.OWNER
        )
        self.manager = User.objects.create_user(
            username="test_manager", password="password", role=User.Role.MANAGER
        )
        self.driver = User.objects.create_user(
            username="test_driver", password="password", role=User.Role.DRIVER
        )
        self.route = Route.objects.create(name="Route A", code="RTA")

    def test_owner_can_access_users_endpoint(self):
        self.client.force_authenticate(user=self.owner)
        url = reverse("api_v1:user-list")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_manager_cannot_access_users_endpoint(self):
        self.client.force_authenticate(user=self.manager)
        url = reverse("api_v1:user-list")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_driver_cannot_access_users_endpoint(self):
        self.client.force_authenticate(user=self.driver)
        url = reverse("api_v1:user-list")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_delete_route(self):
        self.client.force_authenticate(user=self.owner)
        url = reverse("api_v1:route-detail", args=[self.route.id])
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    def test_manager_cannot_delete_route(self):
        self.client.force_authenticate(user=self.manager)
        url = reverse("api_v1:route-detail", args=[self.route.id])
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_driver_cannot_create_route(self):
        self.client.force_authenticate(user=self.driver)
        url = reverse("api_v1:route-list")
        res = self.client.post(url, {"name": "New Route", "code": "NR"})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
