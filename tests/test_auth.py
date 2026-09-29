from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from apps.accounts.models import User

class AuthenticationTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="test_owner",
            password="securepassword123",
            role=User.Role.OWNER,
            email="owner@test.com"
        )
        self.driver = User.objects.create_user(
            username="test_driver",
            password="driverpassword123",
            role=User.Role.DRIVER,
            email="driver@test.com"
        )

    def test_login_successful_and_returns_jwt_with_user_claims(self):
        url = reverse("api_v1:token_obtain_pair")
        response = self.client.post(url, {
            "username": "test_owner",
            "password": "securepassword123"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertIn("user", response.data)
        self.assertEqual(response.data["user"]["role"], "OWNER")
        self.assertEqual(response.data["user"]["username"], "test_owner")

    def test_login_with_invalid_credentials_fails(self):
        url = reverse("api_v1:token_obtain_pair")
        response = self.client.post(url, {
            "username": "test_owner",
            "password": "wrongpassword"
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_refresh(self):
        login_url = reverse("api_v1:token_obtain_pair")
        login_res = self.client.post(login_url, {
            "username": "test_owner",
            "password": "securepassword123"
        })
        refresh_token = login_res.data["refresh"]

        refresh_url = reverse("api_v1:token_refresh")
        refresh_res = self.client.post(refresh_url, {"refresh": refresh_token})
        self.assertEqual(refresh_res.status_code, status.HTTP_200_OK)
        self.assertIn("access", refresh_res.data)

    def test_unauthenticated_request_rejected(self):
        url = reverse("api_v1:user_profile")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_profile_access(self):
        self.client.force_authenticate(user=self.owner)
        url = reverse("api_v1:user_profile")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "test_owner")
        self.assertEqual(response.data["role"], "OWNER")
