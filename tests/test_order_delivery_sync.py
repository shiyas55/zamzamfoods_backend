import datetime
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from apps.customers.models import Customer
from apps.products.models import Product
from apps.routes.models import Route, Driver
from apps.orders.models import Order
from apps.deliveries.models import Delivery
from apps.deliveries.services import ensure_order_delivery

User = get_user_model()

class OrderDeliverySyncFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager_user = User.objects.create_user(
            username="test_mgr",
            email="mgr@zamzam.com",
            password="Password123!",
            role="MANAGER",
            first_name="Test",
            last_name="Manager"
        )
        self.driver_user = User.objects.create_user(
            username="test_driver",
            email="driver@zamzam.com",
            password="Password123!",
            role="DRIVER",
            first_name="Driver",
            last_name="One"
        )
        self.route = Route.objects.create(name="Route Alpha", code="RTA")
        self.driver = Driver.objects.create(
            user=self.driver_user,
            phone_number="9876543210",
            assigned_route=self.route,
            is_active=True
        )
        self.customer = Customer.objects.create(
            name="ABC Shop",
            owner_name="Mr. ABC",
            phone="9998887776",
            address="123 Market Street",
            route=self.route
        )
        self.kubbus = Product.objects.create(
            name="Kubbus",
            code="KBS",
            unit_price=Decimal("35.00"),
            is_active=True
        )
        self.romali = Product.objects.create(
            name="Romali Roti",
            code="PRI",
            unit_price=Decimal("45.00"),
            is_active=True
        )

    def test_order_creation_delivery_sync_and_driver_visibility(self):
        """
        Tests complete Phase 13 requirements:
        1. Manager submits order: Kubbus=10, Romali=5
        2. Database transaction commits Order and OrderItems atomically
        3. Delivery dispatch record is automatically created for Route Alpha driver
        4. Manager queries orders -> returns order with items
        5. Driver queries deliveries -> returns assigned delivery with order items
        6. Other driver cannot see this delivery
        """
        self.client.force_authenticate(user=self.manager_user)
        payload = {
            "customer_id": str(self.customer.id),
            "driver_id": str(self.driver.id),
            "order_date": "2026-10-01",
            "items": [
                {"product_id": str(self.kubbus.id), "quantity": 10},
                {"product_id": str(self.romali.id), "quantity": 5},
            ],
            "notes": "Test Order for Phase 13"
        }
        res = self.client.post("/api/v1/orders/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        order_id = res.data["id"]
        order_number = res.data["order_number"]

        # 1. Verify in Database
        order = Order.objects.get(id=order_id)
        self.assertEqual(order.order_number, order_number)
        self.assertEqual(order.customer, self.customer)
        self.assertEqual(order.route, self.route)
        self.assertEqual(order.driver, self.driver)

        items = {it.product.code: it.quantity for it in order.items.all()}
        self.assertEqual(items.get("KBS"), 10)
        self.assertEqual(items.get("PRI"), 5)

        # 2. Verify Delivery Dispatch Exists
        self.assertTrue(hasattr(order, "delivery"))
        deliv = order.delivery
        self.assertIsNotNone(deliv)
        self.assertEqual(deliv.driver, self.driver)
        self.assertEqual(deliv.route, self.route)
        self.assertEqual(deliv.status, Delivery.Status.ASSIGNED)
        self.assertTrue(deliv.delivery_number.startswith("DEL-20261001-"))

        # 3. Verify Manager Orders API (Simulating hard refresh)
        mgr_res = self.client.get("/api/v1/orders/?date=2026-10-01&all=true")
        self.assertEqual(mgr_res.status_code, status.HTTP_200_OK)
        mgr_orders = mgr_res.data if isinstance(mgr_res.data, list) else mgr_res.data.get("results", [])
        found_mgr_orders = [o for o in mgr_orders if o["id"] == str(order_id)]
        self.assertEqual(len(found_mgr_orders), 1)
        self.assertEqual(str(found_mgr_orders[0]["driver"]), str(self.driver.id))

        # 4. Verify Driver Deliveries API (Driver login & hard refresh)
        self.client.force_authenticate(user=self.driver_user)
        driver_deliv_res = self.client.get("/api/v1/deliveries/?all=true")
        self.assertEqual(driver_deliv_res.status_code, status.HTTP_200_OK)
        driver_stops = driver_deliv_res.data if isinstance(driver_deliv_res.data, list) else driver_deliv_res.data.get("results", [])
        found_stops = [d for d in driver_stops if d["id"] == str(deliv.id)]
        self.assertEqual(len(found_stops), 1)
        self.assertEqual(found_stops[0]["order_details"]["order_number"], order_number)

        # 5. Verify Driver Data Isolation: another driver must NOT see this stop
        other_user = User.objects.create_user(username="driver_two", password="Password123!", role="DRIVER")
        other_driver = Driver.objects.create(user=other_user, is_active=True)
        self.client.force_authenticate(user=other_user)
        other_deliv_res = self.client.get("/api/v1/deliveries/?all=true")
        other_stops = other_deliv_res.data if isinstance(other_deliv_res.data, list) else other_deliv_res.data.get("results", [])
        self.assertEqual(len(other_stops), 0)

    def test_auto_assign_route_driver_when_driver_id_omitted(self):
        """
        When manager submits an order without driver_id, system must resolve
        the driver from customer's route and create a Delivery.
        """
        self.client.force_authenticate(user=self.manager_user)
        payload = {
            "customer_id": str(self.customer.id),
            "order_date": "2026-10-01",
            "items": [
                {"product_id": str(self.kubbus.id), "quantity": 10},
            ],
        }
        res = self.client.post("/api/v1/orders/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        order = Order.objects.get(id=res.data["id"])
        self.assertEqual(order.driver, self.driver)
        self.assertTrue(hasattr(order, "delivery"))
        self.assertEqual(order.delivery.driver, self.driver)
