from decimal import Decimal
import datetime
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User
from apps.routes.models import Route, Driver, DriverExpense
from apps.customers.models import Customer, CustomerProductPrice
from apps.products.models import Product
from apps.orders.models import Order, OrderItem
from apps.deliveries.models import Delivery
from apps.payments.models import Payment
from apps.credits.models import CreditTransaction
from apps.common.models import ActivityLog
from apps.reports.models import DailyClosing


class SecurityAuditAndAuthorizationTestCase(TestCase):
    """
    Prompt 7 Security Audit & Authorization Test Suite:
    Verifies authentication, role isolation, driver data isolation,
    IDOR defenses, mass assignment guards, financial controls, and audit integrity.
    """

    def setUp(self):
        self.client = APIClient()

        # 1. Create Owner User
        self.owner = User.objects.create_user(
            username="owner_audit",
            email="owner_audit@zamzam.com",
            password="StrongOwnerPassword123!",
            role=User.Role.OWNER,
            first_name="Owner",
            last_name="Audit",
        )

        # 2. Create Manager User
        self.manager = User.objects.create_user(
            username="manager_audit",
            email="manager_audit@zamzam.com",
            password="StrongManagerPassword123!",
            role=User.Role.MANAGER,
            first_name="Manager",
            last_name="Audit",
        )

        # 3. Create Routes
        self.route_pandikkad = Route.objects.create(name="Pandikkad", code="PND")
        self.route_melattur = Route.objects.create(name="Melattur", code="MLT")

        # 4. Create Driver A (Pandikkad)
        self.driver_user_a = User.objects.create_user(
            username="driver_a",
            email="driver_a@zamzam.com",
            password="DriverPassword123!",
            role=User.Role.DRIVER,
            first_name="Driver",
            last_name="Alpha",
        )
        self.driver_profile_a = Driver.objects.create(
            user=self.driver_user_a,
            assigned_route=self.route_pandikkad,
            phone_number="9876543210",
            vehicle_number="KL-10-AA-1111",
            is_active=True,
        )

        # 5. Create Driver B (Melattur)
        self.driver_user_b = User.objects.create_user(
            username="driver_b",
            email="driver_b@zamzam.com",
            password="DriverPassword123!",
            role=User.Role.DRIVER,
            first_name="Driver",
            last_name="Beta",
        )
        self.driver_profile_b = Driver.objects.create(
            user=self.driver_user_b,
            assigned_route=self.route_melattur,
            phone_number="9876543211",
            vehicle_number="KL-10-BB-2222",
            is_active=True,
        )

        # 6. Create Customers
        self.customer_pnd = Customer.objects.create(
            name="Pandikkad Hot Bakes",
            phone="9998887771",
            address="Market Road, Pandikkad",
            route=self.route_pandikkad,
            credit_limit=Decimal("5000.00"),
            current_balance=Decimal("1000.00"),
        )
        self.customer_mlt = Customer.objects.create(
            name="Melattur Tea Stall",
            phone="9998887772",
            address="Station Road, Melattur",
            route=self.route_melattur,
            credit_limit=Decimal("3000.00"),
            current_balance=Decimal("500.00"),
        )

        # 7. Create Products
        self.product_kubbus = Product.objects.create(
            name="Kubbus Standard",
            code="KUB-01",
            unit_price=Decimal("10.00"),
            packet_size="10 pieces",
        )

        # 8. Create Orders and Deliveries for Driver A and Driver B
        self.order_a = Order.objects.create(
            order_number="ORD-AUDIT-A001",
            customer=self.customer_pnd,
            route=self.route_pandikkad,
            driver=self.driver_profile_a,
            order_date=timezone.now().date(),
            status=Order.Status.CONFIRMED,
            total_amount=Decimal("500.00"),
        )
        self.delivery_a = Delivery.objects.create(
            delivery_number="DEL-AUDIT-A001",
            order=self.order_a,
            route=self.route_pandikkad,
            driver=self.driver_profile_a,
            status=Delivery.Status.ASSIGNED,
        )

        self.order_b = Order.objects.create(
            order_number="ORD-AUDIT-B001",
            customer=self.customer_mlt,
            route=self.route_melattur,
            driver=self.driver_profile_b,
            order_date=timezone.now().date(),
            status=Order.Status.CONFIRMED,
            total_amount=Decimal("300.00"),
        )
        self.delivery_b = Delivery.objects.create(
            delivery_number="DEL-AUDIT-B001",
            order=self.order_b,
            route=self.route_melattur,
            driver=self.driver_profile_b,
            status=Delivery.Status.ASSIGNED,
        )

        # 9. Create Expenses
        self.expense_a = DriverExpense.objects.create(
            driver=self.driver_profile_a,
            category=DriverExpense.Category.PETROL_FUEL,
            amount=Decimal("250.00"),
            date=timezone.now().date(),
            created_by=self.driver_user_a,
        )
        self.expense_b = DriverExpense.objects.create(
            driver=self.driver_profile_b,
            category=DriverExpense.Category.FOOD,
            amount=Decimal("150.00"),
            date=timezone.now().date(),
            created_by=self.driver_user_b,
        )

        # 10. Create Payments
        self.payment_a = Payment.objects.create(
            payment_number="PAY-AUDIT-A001",
            customer=self.customer_pnd,
            order=self.order_a,
            amount=Decimal("500.00"),
            payment_method=Payment.Method.CASH,
            status=Payment.Status.COMPLETED,
            collected_by=self.driver_user_a,
        )
        self.payment_b = Payment.objects.create(
            payment_number="PAY-AUDIT-B001",
            customer=self.customer_mlt,
            order=self.order_b,
            amount=Decimal("300.00"),
            payment_method=Payment.Method.GPAY_UPI,
            status=Payment.Status.COMPLETED,
            collected_by=self.driver_user_b,
        )

    # -------------------------------------------------------------------------
    # 1. AUTHENTICATION & CREDENTIAL SECURITY
    # -------------------------------------------------------------------------
    def test_password_is_properly_hashed(self):
        """Verify passwords are never stored in plaintext in the database."""
        user = User.objects.get(username="owner_audit")
        self.assertNotEqual(user.password, "StrongOwnerPassword123!")
        self.assertTrue(user.password.startswith("pbkdf2_") or user.password.startswith("argon2") or "sha256" in user.password)
        self.assertTrue(user.check_password("StrongOwnerPassword123!"))

    def test_jwt_login_valid_credentials(self):
        """Verify successful JWT issuance with user details and claims."""
        res = self.client.post("/api/v1/auth/login/", {
            "username": "owner_audit",
            "password": "StrongOwnerPassword123!",
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)
        self.assertEqual(res.data["user"]["role"], "OWNER")

    def test_jwt_login_invalid_credentials_rejected(self):
        """Verify invalid credentials return 401 Unauthorized."""
        res = self.client.post("/api/v1/auth/login/", {
            "username": "owner_audit",
            "password": "WrongPassword!",
        })
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_inactive_user_cannot_login(self):
        """Verify deactivated account is rejected by JWT login."""
        self.driver_user_a.is_active = False
        self.driver_user_a.save()

        res = self.client.post("/api/v1/auth/login/", {
            "username": "driver_a",
            "password": "DriverPassword123!",
        })
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_api_access_rejected(self):
        """Verify unauthenticated requests to protected endpoints return 401."""
        endpoints = [
            "/api/v1/customers/",
            "/api/v1/orders/",
            "/api/v1/deliveries/",
            "/api/v1/driver-expenses/",
            "/api/v1/payments/",
            "/api/v1/credits/",
            "/api/v1/routes/",
            "/api/v1/drivers/",
            "/api/v1/activity-logs/",
        ]
        for ep in endpoints:
            res = self.client.get(ep)
            self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED, f"Endpoint {ep} failed unauthenticated check.")

    # -------------------------------------------------------------------------
    # 2. ROLE SECURITY & USER ADMINISTRATION RESTRICTIONS
    # -------------------------------------------------------------------------
    def test_non_owners_forbidden_from_user_management(self):
        """Manager and Driver cannot view or create users via /api/v1/auth/users/."""
        # Manager
        self.client.force_authenticate(user=self.manager)
        res_mgr = self.client.get("/api/v1/auth/users/")
        self.assertEqual(res_mgr.status_code, status.HTTP_403_FORBIDDEN)

        # Driver
        self.client.force_authenticate(user=self.driver_user_a)
        res_drv = self.client.get("/api/v1/auth/users/")
        self.assertEqual(res_drv.status_code, status.HTTP_403_FORBIDDEN)

        res_create = self.client.post("/api/v1/auth/users/", {
            "username": "fake_owner",
            "email": "fake@zamzam.com",
            "password": "FakePassword123!",
            "role": "OWNER",
        })
        self.assertEqual(res_create.status_code, status.HTTP_403_FORBIDDEN)

    # -------------------------------------------------------------------------
    # 3. DRIVER ISOLATION (Driver A vs Driver B)
    # -------------------------------------------------------------------------
    def test_driver_cannot_access_other_driver_deliveries(self):
        """Driver A cannot access Driver B's deliveries via direct ID (IDOR defense)."""
        self.client.force_authenticate(user=self.driver_user_a)

        # Can see own delivery
        res_own = self.client.get(f"/api/v1/deliveries/{self.delivery_a.id}/")
        self.assertEqual(res_own.status_code, status.HTTP_200_OK)

        # Cannot see other driver's delivery
        res_other = self.client.get(f"/api/v1/deliveries/{self.delivery_b.id}/")
        self.assertEqual(res_other.status_code, status.HTTP_404_NOT_FOUND)

        # Cannot complete other driver's delivery
        res_complete = self.client.post(f"/api/v1/deliveries/{self.delivery_b.id}/complete/", {
            "recipient_name": "Tampered Recipient",
        })
        self.assertEqual(res_complete.status_code, status.HTTP_404_NOT_FOUND)

        # Cannot mark other driver's delivery as not delivered
        res_fail = self.client.post(f"/api/v1/deliveries/{self.delivery_b.id}/mark-not-delivered/", {
            "failed_reason": "Shop closed",
        })
        self.assertEqual(res_fail.status_code, status.HTTP_404_NOT_FOUND)

    def test_driver_cannot_access_other_driver_expenses(self):
        """Driver A cannot access or modify Driver B's expenses."""
        self.client.force_authenticate(user=self.driver_user_a)

        # Direct GET
        res_get = self.client.get(f"/api/v1/driver-expenses/{self.expense_b.id}/")
        self.assertEqual(res_get.status_code, status.HTTP_404_NOT_FOUND)

        # Direct PATCH
        res_patch = self.client.patch(f"/api/v1/driver-expenses/{self.expense_b.id}/", {
            "amount": "999.00",
        })
        self.assertEqual(res_patch.status_code, status.HTTP_404_NOT_FOUND)

        # Direct DELETE
        res_del = self.client.delete(f"/api/v1/driver-expenses/{self.expense_b.id}/")
        self.assertEqual(res_del.status_code, status.HTTP_404_NOT_FOUND)

    def test_driver_cannot_access_other_driver_collections(self):
        """Driver A cannot view Driver B's payments."""
        self.client.force_authenticate(user=self.driver_user_a)

        # Direct GET on payment B
        res_pay = self.client.get(f"/api/v1/payments/{self.payment_b.id}/")
        self.assertEqual(res_pay.status_code, status.HTTP_404_NOT_FOUND)

    def test_driver_cannot_access_other_route_customers(self):
        """Driver A (Pandikkad) cannot access customer on Melattur route."""
        self.client.force_authenticate(user=self.driver_user_a)

        # Customer on Melattur route
        res_cust = self.client.get(f"/api/v1/customers/{self.customer_mlt.id}/")
        self.assertEqual(res_cust.status_code, status.HTTP_404_NOT_FOUND)

        res_sum = self.client.get(f"/api/v1/customers/{self.customer_mlt.id}/summary/")
        self.assertEqual(res_sum.status_code, status.HTTP_404_NOT_FOUND)

    def test_driver_cannot_view_other_driver_performance(self):
        """Driver A cannot view Driver B's performance details."""
        self.client.force_authenticate(user=self.driver_user_a)

        # View B's drilldown
        res = self.client.get(f"/api/v1/reports/driver-performance/{self.driver_profile_b.id}/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # -------------------------------------------------------------------------
    # 4. MASS ASSIGNMENT & READ-ONLY FIELD PROTECTION
    # -------------------------------------------------------------------------
    def test_customer_current_balance_is_not_writable(self):
        """A user cannot directly inject or modify customer current_balance via API."""
        self.client.force_authenticate(user=self.manager)

        res = self.client.patch(f"/api/v1/customers/{self.customer_pnd.id}/", {
            "current_balance": "0.00",
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.customer_pnd.refresh_from_db()
        self.assertEqual(self.customer_pnd.current_balance, Decimal("1000.00"))

    def test_driver_expense_creation_forces_authenticated_driver(self):
        """Even if Driver A passes Driver B's ID in payload, it is assigned to Driver A."""
        self.client.force_authenticate(user=self.driver_user_a)

        res = self.client.post("/api/v1/driver-expenses/", {
            "driver": str(self.driver_profile_b.id),  # Attempted impersonation
            "category": "PETROL_FUEL",
            "amount": "300.00",
            "date": str(timezone.now().date()),
            "notes": "Testing impersonation defense",
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        created_exp = DriverExpense.objects.get(id=res.data["id"])
        self.assertEqual(created_exp.driver, self.driver_profile_a)
        self.assertEqual(created_exp.created_by, self.driver_user_a)

    def test_driver_expense_driver_field_is_read_only_on_update(self):
        """Updating an existing expense cannot reassign it to another driver."""
        self.client.force_authenticate(user=self.driver_user_a)

        res = self.client.patch(f"/api/v1/driver-expenses/{self.expense_a.id}/", {
            "driver": str(self.driver_profile_b.id),
            "amount": "260.00",
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.expense_a.refresh_from_db()
        self.assertEqual(self.expense_a.driver, self.driver_profile_a)

    # -------------------------------------------------------------------------
    # 5. FINANCIAL SECURITY & TAMPERING PREVENTION
    # -------------------------------------------------------------------------
    def test_driver_cannot_create_or_modify_orders(self):
        """Driver cannot place orders or alter order line items."""
        self.client.force_authenticate(user=self.driver_user_a)

        res_create = self.client.post("/api/v1/orders/", {
            "customer_id": str(self.customer_pnd.id),
            "items": [{"product_id": str(self.product_kubbus.id), "quantity": 10}],
        })
        self.assertEqual(res_create.status_code, status.HTTP_403_FORBIDDEN)

        res_patch = self.client.patch(f"/api/v1/orders/{self.order_a.id}/", {
            "notes": "Driver tampering",
        })
        self.assertEqual(res_patch.status_code, status.HTTP_403_FORBIDDEN)

    def test_driver_cannot_modify_customer_pricing(self):
        """Driver cannot access or configure wholesale product prices."""
        self.client.force_authenticate(user=self.driver_user_a)

        res = self.client.post(f"/api/v1/customers/{self.customer_pnd.id}/pricing/", {
            "product_id": str(self.product_kubbus.id),
            "price": "1.00",
        })
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        res_list = self.client.get("/api/v1/customer-prices/")
        self.assertEqual(res_list.status_code, status.HTTP_403_FORBIDDEN)

    def test_driver_cannot_adjust_customer_credit(self):
        """Driver cannot create manual credit ledger adjustments."""
        self.client.force_authenticate(user=self.driver_user_a)

        res = self.client.post("/api/v1/credits/adjust/", {
            "customer_id": str(self.customer_pnd.id),
            "amount": "-500.00",
            "notes": "Unauthorized driver credit waiver",
        })
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_driver_cannot_collect_for_other_driver_order(self):
        """Driver A cannot collect payment for Driver B's order."""
        self.client.force_authenticate(user=self.driver_user_a)

        res = self.client.post("/api/v1/payments/", {
            "customer_id": str(self.customer_mlt.id),
            "order_id": str(self.order_b.id),
            "amount": "300.00",
            "payment_method": "CASH",
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Drivers can only collect payments", str(res.data))

    def test_negative_financial_inputs_rejected(self):
        """Negative unit prices, negative payments, and negative expenses are rejected."""
        self.client.force_authenticate(user=self.manager)

        # 1. Negative unit price on order creation
        res_order = self.client.post("/api/v1/orders/", {
            "customer_id": str(self.customer_pnd.id),
            "items": [
                {
                    "product_id": str(self.product_kubbus.id),
                    "quantity": 10,
                    "unit_price": "-5.00",
                }
            ],
        }, format="json")
        self.assertEqual(res_order.status_code, status.HTTP_400_BAD_REQUEST)

        # 2. Negative payment
        res_pay = self.client.post("/api/v1/payments/", {
            "customer_id": str(self.customer_pnd.id),
            "amount": "-100.00",
            "payment_method": "CASH",
        })
        self.assertEqual(res_pay.status_code, status.HTTP_400_BAD_REQUEST)

        # 3. Negative expense
        res_exp = self.client.post("/api/v1/driver-expenses/", {
            "driver": str(self.driver_profile_a.id),
            "category": "PETROL_FUEL",
            "amount": "-50.00",
            "date": str(timezone.now().date()),
        })
        self.assertEqual(res_exp.status_code, status.HTTP_400_BAD_REQUEST)

        # 4. Negative customer credit limit
        res_cust = self.client.post("/api/v1/customers/", {
            "name": "Invalid Credit Shop",
            "phone": "9998881111",
            "address": "Test Town",
            "route": str(self.route_pandikkad.id),
            "credit_limit": "-1000.00",
        })
        self.assertEqual(res_cust.status_code, status.HTTP_400_BAD_REQUEST)

    # -------------------------------------------------------------------------
    # 6. DELIVERY BYPASS PREVENTION
    # -------------------------------------------------------------------------
    def test_driver_cannot_directly_patch_or_delete_deliveries(self):
        """Driver cannot bypass complete_delivery_service via direct PATCH/DELETE."""
        self.client.force_authenticate(user=self.driver_user_a)

        # Direct PATCH status
        res_patch = self.client.patch(f"/api/v1/deliveries/{self.delivery_a.id}/", {
            "status": "DELIVERED",
        })
        self.assertEqual(res_patch.status_code, status.HTTP_403_FORBIDDEN)

        # Direct DELETE
        res_del = self.client.delete(f"/api/v1/deliveries/{self.delivery_a.id}/")
        self.assertEqual(res_del.status_code, status.HTTP_403_FORBIDDEN)

        # Direct POST (create delivery)
        res_post = self.client.post("/api/v1/deliveries/", {
            "order": str(self.order_a.id),
            "route": str(self.route_pandikkad.id),
        })
        self.assertEqual(res_post.status_code, status.HTTP_403_FORBIDDEN)

    # -------------------------------------------------------------------------
    # 7. AUDIT LOG IMMUTABILITY & ACCESS RESTRICTION
    # -------------------------------------------------------------------------
    def test_driver_cannot_view_audit_logs(self):
        """Driver receives 403 Forbidden on activity log access."""
        self.client.force_authenticate(user=self.driver_user_a)
        res = self.client.get("/api/v1/activity-logs/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_audit_logs_cannot_be_modified_or_deleted_by_anyone(self):
        """ActivityLog is read-only for all users (POST, PUT, DELETE return 405)."""
        self.client.force_authenticate(user=self.owner)

        res_post = self.client.post("/api/v1/activity-logs/", {
            "summary": "Fake log",
        })
        self.assertEqual(res_post.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # Create one log directly in DB
        log = ActivityLog.objects.create(
            user=self.owner,
            user_name="Owner",
            user_role="OWNER",
            action="CREATED",
            entity_type="SYSTEM",
            summary="System setup",
        )

        res_del = self.client.delete(f"/api/v1/activity-logs/{log.id}/")
        self.assertEqual(res_del.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        res_patch = self.client.patch(f"/api/v1/activity-logs/{log.id}/", {
            "summary": "Tampered log",
        })
        self.assertEqual(res_patch.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    # -------------------------------------------------------------------------
    # 8. DAILY CLOSING PERMISSION RESTRICTIONS
    # -------------------------------------------------------------------------
    def test_manager_can_close_day_but_cannot_reopen(self):
        """Manager can perform daily closing, but reopening is Owner-only."""
        self.client.force_authenticate(user=self.manager)
        today_str = str(timezone.now().date())

        # Manager closes day
        res_close = self.client.post("/api/v1/reports/daily-closing/", {
            "date": today_str,
            "checklist": {
                "physical_cash_verified": True,
                "upi_verified": True,
                "expenses_verified": True,
            },
        }, format="json")
        self.assertEqual(res_close.status_code, status.HTTP_201_CREATED)

        # Manager attempts reopen -> 403 Forbidden
        res_reopen = self.client.post("/api/v1/reports/daily-closing/reopen/", {
            "date": today_str,
            "reason": "Manager trying to reopen",
        })
        self.assertEqual(res_reopen.status_code, status.HTTP_403_FORBIDDEN)

        # Owner reopens -> 200 OK
        self.client.force_authenticate(user=self.owner)
        res_owner_reopen = self.client.post("/api/v1/reports/daily-closing/reopen/", {
            "date": today_str,
            "reason": "Owner authorized adjustment of delayed cash deposit",
        })
        self.assertEqual(res_owner_reopen.status_code, status.HTTP_200_OK)
