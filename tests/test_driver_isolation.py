from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from apps.accounts.models import User
from apps.routes.models import Route, Driver
from apps.customers.models import Customer
from apps.products.models import Product
from apps.orders.services import create_order_service
from apps.deliveries.models import Delivery

class DriverDataIsolationTests(APITestCase):
    def setUp(self):
        # Create 2 routes
        self.route_pandikkad = Route.objects.create(name="Pandikkad", code="PKD")
        self.route_perundurai = Route.objects.create(name="Perundurai", code="PRD")

        # Create Driver A (Pandikkad)
        self.user_driver_a = User.objects.create_user(
            username="driver_a", password="password", role=User.Role.DRIVER
        )
        self.driver_a = Driver.objects.create(
            user=self.user_driver_a,
            assigned_route=self.route_pandikkad,
            phone_number="9847111111",
            vehicle_number="KL-10-A-1111"
        )

        # Create Driver B (Perundurai)
        self.user_driver_b = User.objects.create_user(
            username="driver_b", password="password", role=User.Role.DRIVER
        )
        self.driver_b = Driver.objects.create(
            user=self.user_driver_b,
            assigned_route=self.route_perundurai,
            phone_number="9847222222",
            vehicle_number="KL-10-B-2222"
        )

        # Create Shops
        self.shop_a = Customer.objects.create(
            name="Shop in Pandikkad",
            phone="9847100001",
            address="Pandikkad",
            route=self.route_pandikkad,
        )
        self.shop_b = Customer.objects.create(
            name="Shop in Perundurai",
            phone="9847200001",
            address="Perundurai",
            route=self.route_perundurai,
        )

        # Create Product
        self.product = Product.objects.create(
            name="Kubbus",
            code="KUB",
            unit_price=Decimal("35.00"),
        )

        # Order & Delivery for Driver A
        self.order_a = create_order_service(
            customer_id=self.shop_a.id,
            items_data=[{"product_id": self.product.id, "quantity": 10}],
            driver_id=self.driver_a.id,
        )
        self.delivery_a = self.order_a.delivery

        # Order & Delivery for Driver B
        self.order_b = create_order_service(
            customer_id=self.shop_b.id,
            items_data=[{"product_id": self.product.id, "quantity": 20}],
            driver_id=self.driver_b.id,
        )
        self.delivery_b = self.order_b.delivery

    def test_driver_a_can_access_own_delivery(self):
        self.client.force_authenticate(user=self.user_driver_a)
        url = reverse("api_v1:delivery-detail", args=[self.delivery_a.id])
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["delivery_number"], self.delivery_a.delivery_number)

    def test_driver_a_cannot_access_driver_b_delivery_by_id(self):
        """
        CRITICAL TEST: Driver A must never be able to retrieve Driver B's deliveries
        by changing an ID in the URL. Must return 404 Not Found.
        """
        self.client.force_authenticate(user=self.user_driver_a)
        url = reverse("api_v1:delivery-detail", args=[self.delivery_b.id])
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_driver_a_cannot_complete_driver_b_delivery(self):
        """
        Driver A cannot complete Driver B's delivery.
        """
        self.client.force_authenticate(user=self.user_driver_a)
        url = reverse("api_v1:delivery-complete", args=[self.delivery_b.id])
        res = self.client.post(url, {"recipient_name": "Unauthorized Attempt"})
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_driver_a_delivery_list_only_contains_driver_a_deliveries(self):
        self.client.force_authenticate(user=self.user_driver_a)
        url = reverse("api_v1:delivery-list")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        # Results can be in res.data["results"] if paginated or res.data
        results = res.data.get("results", res.data)
        ids = [item["id"] for item in results]
        self.assertIn(str(self.delivery_a.id), ids)
        self.assertNotIn(str(self.delivery_b.id), ids)

    def test_driver_a_cannot_view_shops_on_another_route(self):
        self.client.force_authenticate(user=self.user_driver_a)
        url = reverse("api_v1:customer-detail", args=[self.shop_b.id])
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
