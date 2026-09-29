from decimal import Decimal
import datetime
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from apps.accounts.models import User
from apps.customers.models import Customer, CustomerProductPrice
from apps.products.models import Product
from apps.routes.models import Route, Driver
from apps.orders.models import Order, OrderItem
from apps.deliveries.models import Delivery
from apps.payments.models import Payment
from apps.credits.models import CreditTransaction
from apps.reports.models import DailyClosing
from apps.common.models import ActivityLog

class Prompt4ManagerOperationsTests(APITestCase):
    def setUp(self):
        # Users
        self.owner = User.objects.create_user(
            username="owner_user",
            email="owner@zamzam.com",
            password="OwnerPassword123!",
            role=User.Role.OWNER,
            first_name="Farooq",
            last_name="Owner",
        )
        self.manager = User.objects.create_user(
            username="manager_user",
            email="manager@zamzam.com",
            password="ManagerPassword123!",
            role=User.Role.MANAGER,
            first_name="Zayd",
            last_name="Manager",
        )
        self.driver_user_1 = User.objects.create_user(
            username="driver_pandikkad",
            email="driver1@zamzam.com",
            password="DriverPassword123!",
            role=User.Role.DRIVER,
            first_name="Bilal",
            last_name="Driver",
        )
        self.driver_user_2 = User.objects.create_user(
            username="driver_melattur",
            email="driver2@zamzam.com",
            password="DriverPassword123!",
            role=User.Role.DRIVER,
            first_name="Tariq",
            last_name="Driver",
        )

        # Routes
        self.route_pandikkad = Route.objects.create(name="Pandikkad Route", code="PKD")
        self.route_melattur = Route.objects.create(name="Melattur Route", code="MLT")

        # Drivers
        self.driver_1 = Driver.objects.create(
            user=self.driver_user_1,
            assigned_route=self.route_pandikkad,
            vehicle_number="KL-10-AB-1111",
            phone_number="9876543210",
        )
        self.driver_2 = Driver.objects.create(
            user=self.driver_user_2,
            assigned_route=self.route_melattur,
            vehicle_number="KL-10-CD-2222",
            phone_number="9876543211",
        )

        # Products
        self.kubbus = Product.objects.create(
            name="Kubbus",
            code="KUB-01",
            unit_price=Decimal("12.00"),
            packet_size="10 pcs",
        )
        self.romali = Product.objects.create(
            name="Romali Roti",
            code="ROM-01",
            unit_price=Decimal("20.00"),
            packet_size="5 pcs",
        )


        # Customer with custom price (Kubbus @ 10.50 instead of 12.00)
        self.customer = Customer.objects.create(
            name="Al-Madina Bakery",
            owner_name="Moideen",
            phone="9988776655",
            route=self.route_pandikkad,
            current_balance=Decimal("1500.00"),
        )
        CustomerProductPrice.objects.create(
            customer=self.customer,
            product=self.kubbus,
            price=Decimal("10.50"),
        )


    # 1. FAST ORDER CREATION WITH CUSTOMER PRICING & OVERRIDE
    def test_fast_order_creation_with_pricing_and_override(self):
        self.client.force_authenticate(user=self.manager)

        # Create order using customer specific price for Kubbus, and explicit price override for Romali
        payload = {
            "customer_id": str(self.customer.id),
            "driver_id": str(self.driver_1.id),
            "notes": "Express morning delivery",
            "items": [
                {"product_id": str(self.kubbus.id), "quantity": 10},  # should use customer price 10.50
                {"product_id": str(self.romali.id), "quantity": 5, "unit_price": "18.50"},  # manager override
            ]
        }
        response = self.client.post("/api/v1/orders/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.data

        # Total = 10 * 10.50 + 5 * 18.50 = 105.00 + 92.50 = 197.50
        self.assertEqual(Decimal(str(data["total_amount"])), Decimal("197.50"))
        self.assertEqual(data["driver_name"], "Bilal Driver")

        # Verify auto-created delivery
        delivery = Delivery.objects.filter(order_id=data["id"]).first()
        self.assertIsNotNone(delivery)
        self.assertEqual(delivery.driver, self.driver_1)
        self.assertEqual(delivery.status, Delivery.Status.ASSIGNED)

    # 2. REPEAT ORDER: LOADS CURRENT PRICING, NOT OBSOLETE HISTORICAL PRICING
    def test_repeat_order_resolves_current_pricing(self):
        self.client.force_authenticate(user=self.manager)

        # Create historical order when Kubbus was 10.50
        old_order = Order.objects.create(
            order_number="ORD-HIST-001",
            customer=self.customer,
            route=self.route_pandikkad,
            driver=self.driver_1,
            total_amount=Decimal("105.00"),
            order_date=timezone.now().date() - datetime.timedelta(days=7),
            status=Order.Status.DELIVERED,
        )
        OrderItem.objects.create(
            order=old_order,
            product=self.kubbus,
            quantity=10,
            unit_price=Decimal("10.50"),
            subtotal=Decimal("105.00"),
        )

        # Later, price increases to 11.25
        CustomerProductPrice.objects.filter(customer=self.customer, product=self.kubbus).update(
            price=Decimal("11.25")
        )


        # Customer summary endpoint returns last order with current_unit_price
        summary_res = self.client.get(f"/api/v1/customers/{self.customer.id}/summary/")
        self.assertEqual(summary_res.status_code, status.HTTP_200_OK)
        last_order = summary_res.data["last_order"]
        self.assertIsNotNone(last_order)
        item = last_order["items"][0]
        self.assertEqual(Decimal(str(item["historical_unit_price"])), Decimal("10.50"))
        self.assertEqual(Decimal(str(item["current_unit_price"])), Decimal("11.25"))
        self.assertTrue(item["price_changed"])

    # 3. ADD CUSTOMER DURING BILLING
    def test_manager_can_create_customer_during_billing(self):
        self.client.force_authenticate(user=self.manager)
        payload = {
            "name": "New Town Supermarket",
            "owner_name": "Hamza",
            "phone": "9998887776",
            "address": "Main Bazaar, Pandikkad",
            "route": str(self.route_pandikkad.id),
            "credit_limit": "8000.00",
        }
        res = self.client.post("/api/v1/customers/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        new_cust_id = res.data["id"]

        # Directly create order for this newly created customer
        order_res = self.client.post("/api/v1/orders/", {
            "customer_id": new_cust_id,
            "items": [{"product_id": str(self.kubbus.id), "quantity": 20}]
        }, format="json")
        self.assertEqual(order_res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(str(order_res.data["customer"]), new_cust_id)


    # 4. ORDER EDITING BEFORE DELIVERED STATE
    def test_order_editing_before_delivery(self):
        self.client.force_authenticate(user=self.manager)

        # Initial order
        order_res = self.client.post("/api/v1/orders/", {
            "customer_id": str(self.customer.id),
            "driver_id": str(self.driver_1.id),
            "items": [{"product_id": str(self.kubbus.id), "quantity": 10}]  # 105.00
        }, format="json")
        order_id = order_res.data["id"]
        self.assertEqual(Decimal(str(order_res.data["total_amount"])), Decimal("105.00"))

        # Edit order: update quantity to 20 and add Romali 5
        edit_payload = {
            "items": [
                {"product_id": str(self.kubbus.id), "quantity": 20},  # 20 * 10.50 = 210.00
                {"product_id": str(self.romali.id), "quantity": 5},   # 5 * 20.00 = 100.00
            ],
            "notes": "Updated quantity by shopkeeper phone request",
        }
        patch_res = self.client.patch(f"/api/v1/orders/{order_id}/", edit_payload, format="json")
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(str(patch_res.data["total_amount"])), Decimal("310.00"))

        # Verify ActivityLog created for financial change
        log = ActivityLog.objects.filter(entity_id=order_id, action="UPDATED").first()
        self.assertIsNotNone(log)
        self.assertIn("310.00", log.summary)

    # 5. ORDER EDITING BLOCKED IF DELIVERED OR CANCELLED
    def test_order_editing_blocked_when_delivered(self):
        self.client.force_authenticate(user=self.manager)
        order = Order.objects.create(
            order_number="ORD-DELIV-001",
            customer=self.customer,
            route=self.route_pandikkad,
            driver=self.driver_1,
            total_amount=Decimal("100.00"),
            status=Order.Status.DELIVERED,
        )
        res = self.client.patch(f"/api/v1/orders/{order.id}/", {
            "items": [{"product_id": str(self.kubbus.id), "quantity": 5}]
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already Delivered", str(res.data))

    # 6. DRIVER ASSIGNMENT WITH ROUTE COMPATIBILITY CHECKS
    def test_driver_assignment_and_route_compatibility(self):
        self.client.force_authenticate(user=self.manager)

        # Create delivery on Pandikkad route
        order = Order.objects.create(
            order_number="ORD-ROUTETEST-01",
            customer=self.customer,
            route=self.route_pandikkad,
            total_amount=Decimal("150.00"),
            status=Order.Status.PENDING,
        )
        delivery = Delivery.objects.create(
            delivery_number="DEL-ROUTETEST-01",
            order=order,
            driver=self.driver_1,
            route=self.route_pandikkad,
            status=Delivery.Status.ASSIGNED,
        )

        # Try to assign Driver 2 (Melattur route) without override -> SHOULD FAIL
        fail_res = self.client.post(f"/api/v1/deliveries/{delivery.id}/assign-driver/", {
            "driver_id": str(self.driver_2.id),
            "allow_cross_route": False,
        }, format="json")
        self.assertEqual(fail_res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("does not match delivery route", fail_res.data["detail"])

        # Assign with allow_cross_route = True -> SHOULD SUCCEED
        success_res = self.client.post(f"/api/v1/deliveries/{delivery.id}/assign-driver/", {
            "driver_id": str(self.driver_2.id),
            "allow_cross_route": True,
        }, format="json")
        self.assertEqual(success_res.status_code, status.HTTP_200_OK)
        delivery.refresh_from_db()
        self.assertEqual(delivery.driver, self.driver_2)
        self.assertEqual(delivery.status, Delivery.Status.ASSIGNED)

    # 7. DRIVER ACTIVE DELIVERIES COUNT
    def test_driver_active_deliveries_count(self):
        self.client.force_authenticate(user=self.manager)
        order = Order.objects.create(
            order_number="ORD-COUNT-01",
            customer=self.customer,
            route=self.route_pandikkad,
            driver=self.driver_1,
            order_date=timezone.now().date(),
            total_amount=Decimal("50.00"),
        )
        Delivery.objects.create(
            delivery_number="DEL-COUNT-01",
            order=order,
            driver=self.driver_1,
            route=self.route_pandikkad,
            status=Delivery.Status.ASSIGNED,
        )

        res = self.client.get("/api/v1/drivers/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        drivers = res.data.get("results", res.data)
        d1 = next(d for d in drivers if d["id"] == str(self.driver_1.id))
        self.assertGreaterEqual(d1["active_deliveries_count"], 1)

    # 8. NOT DELIVERED REASON ENFORCEMENT
    def test_not_delivered_requires_reason(self):
        self.client.force_authenticate(user=self.manager)
        order = Order.objects.create(
            order_number="ORD-FAIL-01",
            customer=self.customer,
            route=self.route_pandikkad,
            driver=self.driver_1,
            total_amount=Decimal("80.00"),
        )
        delivery = Delivery.objects.create(
            delivery_number="DEL-FAIL-01",
            order=order,
            driver=self.driver_1,
            route=self.route_pandikkad,
            status=Delivery.Status.ASSIGNED,
        )

        # Missing reason
        fail_res = self.client.post(f"/api/v1/deliveries/{delivery.id}/mark-not-delivered/", {}, format="json")
        self.assertEqual(fail_res.status_code, status.HTTP_400_BAD_REQUEST)

        # With reason
        success_res = self.client.post(f"/api/v1/deliveries/{delivery.id}/mark-not-delivered/", {
            "failed_reason": "Shop closed",
            "notes": "Arrived at 11 AM, shutter was down",
        }, format="json")
        self.assertEqual(success_res.status_code, status.HTTP_200_OK)
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, Delivery.Status.NOT_DELIVERED)
        self.assertEqual(delivery.failed_reason, "Shop closed")

    # 9. DISTINGUISH TODAY'S ORDER PAYMENT VS PREVIOUS CREDIT PAYMENT
    def test_payment_type_distinction(self):
        self.client.force_authenticate(user=self.manager)
        order = Order.objects.create(
            order_number="ORD-PAY-01",
            customer=self.customer,
            route=self.route_pandikkad,
            total_amount=Decimal("500.00"),
        )

        # 1) Payment tied to order
        pay_order = self.client.post("/api/v1/payments/", {
            "customer_id": str(self.customer.id),
            "order_id": str(order.id),
            "amount": "500.00",
            "payment_method": "CASH",
        }, format="json")
        self.assertEqual(pay_order.status_code, status.HTTP_201_CREATED)
        self.assertEqual(pay_order.data["payment_type"], "ORDER_PAYMENT")

        # 2) Payment without order (paying down previous credit balance)
        pay_credit = self.client.post("/api/v1/payments/", {
            "customer_id": str(self.customer.id),
            "amount": "300.00",
            "payment_method": "GPAY_UPI",
            "reference_number": "UPI998877",
        }, format="json")
        self.assertEqual(pay_credit.status_code, status.HTTP_201_CREATED)
        self.assertEqual(pay_credit.data["payment_type"], "PREVIOUS_CREDIT")

        # Filter by payment_type
        order_pays_res = self.client.get("/api/v1/payments/?payment_type=ORDER_PAYMENT")
        order_pays = order_pays_res.data.get("results", order_pays_res.data)
        self.assertTrue(all(p["payment_type"] == "ORDER_PAYMENT" for p in order_pays))

        credit_pays_res = self.client.get("/api/v1/payments/?payment_type=PREVIOUS_CREDIT")
        credit_pays = credit_pays_res.data.get("results", credit_pays_res.data)
        self.assertTrue(all(p["payment_type"] == "PREVIOUS_CREDIT" for p in credit_pays))


    # 10. DAILY CLOSING WORKFLOW & REOPENING PERMISSION CONTROL
    def test_daily_closing_review_submission_and_owner_reopen(self):
        today_str = timezone.now().strftime("%Y-%m-%d")

        # Manager checks review endpoint
        self.client.force_authenticate(user=self.manager)
        review_res = self.client.get(f"/api/v1/reports/daily-closing/?date={today_str}")
        self.assertEqual(review_res.status_code, status.HTTP_200_OK)
        self.assertFalse(review_res.data["is_closed"])
        self.assertIn("figures", review_res.data)

        # Manager submits closing
        close_res = self.client.post("/api/v1/reports/daily-closing/", {
            "date": today_str,
            "notes": "All deliveries completed and cash verified."
        }, format="json")
        self.assertEqual(close_res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(close_res.data["is_closed"])

        # Second closing attempt should be rejected
        double_close_res = self.client.post("/api/v1/reports/daily-closing/", {
            "date": today_str,
        }, format="json")
        self.assertEqual(double_close_res.status_code, status.HTTP_400_BAD_REQUEST)

        # Manager tries to reopen -> FORBIDDEN (HTTP 403)
        manager_reopen = self.client.post("/api/v1/reports/daily-closing/reopen/", {
            "date": today_str,
            "reason": "Late collection adjustment",
        }, format="json")
        self.assertEqual(manager_reopen.status_code, status.HTTP_403_FORBIDDEN)

        # Owner reopens -> SUCCESS (HTTP 200)
        self.client.force_authenticate(user=self.owner)
        owner_reopen = self.client.post("/api/v1/reports/daily-closing/reopen/", {
            "date": today_str,
            "reason": "Authorized late invoice adjustment by Owner",
        }, format="json")
        self.assertEqual(owner_reopen.status_code, status.HTTP_200_OK)
        self.assertFalse(owner_reopen.data["is_closed"])

    # 11. MANAGER ACCESS SECURITY RESTRICTIONS
    def test_manager_access_restrictions(self):
        self.client.force_authenticate(user=self.manager)

        # Manager cannot create/change user roles
        user_res = self.client.post("/api/v1/auth/users/", {
            "username": "hacked_owner",
            "password": "Password123!",
            "role": "OWNER",
        }, format="json")
        self.assertEqual(user_res.status_code, status.HTTP_403_FORBIDDEN)

        # Manager cannot delete routes
        del_route_res = self.client.delete(f"/api/v1/routes/{self.route_pandikkad.id}/")
        self.assertEqual(del_route_res.status_code, status.HTTP_403_FORBIDDEN)
