from decimal import Decimal
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from apps.accounts.models import User
from apps.routes.models import Route, Driver, DriverExpense
from apps.customers.models import Customer
from apps.products.models import Product
from apps.orders.models import Order, OrderItem
from apps.deliveries.models import Delivery
from apps.payments.models import Payment
from apps.common.models import ActivityLog

class DriverWorkflowPrompt5Tests(APITestCase):
    """
    Automated integration tests for Prompt 5:
    Driver Mobile PWA + Delivery + Collection + Expense Workflow
    """

    def setUp(self):
        # 1. Routes
        self.route_pandikkad = Route.objects.create(name="Pandikkad Route", code="PND")
        self.route_melattur = Route.objects.create(name="Melattur Route", code="MLT")

        # 2. Driver Users & Driver Profiles
        self.driver_user = User.objects.create_user(
            username="driver_ali",
            password="driverpassword123",
            role=User.Role.DRIVER,
            first_name="Ali",
            last_name="Driver",
        )
        self.driver_profile = Driver.objects.create(
            user=self.driver_user,
            assigned_route=self.route_pandikkad,
            vehicle_number="KL-53-E-1001",
            phone_number="9847111222",
        )

        self.driver_other_user = User.objects.create_user(
            username="driver_rafeeq",
            password="driverpassword123",
            role=User.Role.DRIVER,
            first_name="Rafeeq",
            last_name="Driver",
        )
        self.driver_other_profile = Driver.objects.create(
            user=self.driver_other_user,
            assigned_route=self.route_melattur,
            vehicle_number="KL-53-E-2002",
            phone_number="9847333444",
        )

        # 3. Customer Shops
        self.customer1 = Customer.objects.create(
            name="Apsara Tea Stall",
            owner_name="Moideen",
            phone="9847999888",
            address="Near Junction, Pandikkad",
            route=self.route_pandikkad,
            current_balance=Decimal("2500.00"),
        )
        self.customer2 = Customer.objects.create(
            name="Modern Bakery",
            owner_name="Yousuf",
            phone="9847777666",
            address="Bus Stand, Pandikkad",
            route=self.route_pandikkad,
            current_balance=Decimal("1200.00"),
        )
        self.other_route_customer = Customer.objects.create(
            name="Melattur Bakers",
            owner_name="Kareem",
            phone="9847555666",
            address="Town, Melattur",
            route=self.route_melattur,
            current_balance=Decimal("500.00"),
        )

        # 4. Products
        self.kubbus = Product.objects.create(
            name="Kubbus",
            code="KUB-10",
            unit_price=Decimal("10.00"),
            packet_size="10 pieces",
        )

        # 5. Orders & Deliveries
        self.order1 = Order.objects.create(
            order_number="ORD-P5-0001",
            customer=self.customer1,
            route=self.route_pandikkad,
            driver=self.driver_profile,
            total_amount=Decimal("500.00"),
            order_date=timezone.now().date(),
            status=Order.Status.CONFIRMED,
        )
        OrderItem.objects.create(order=self.order1, product=self.kubbus, quantity=50, unit_price=Decimal("10.00"), subtotal=Decimal("500.00"))
        self.delivery1 = Delivery.objects.create(
            delivery_number="DEL-P5-0001",
            order=self.order1,
            route=self.route_pandikkad,
            driver=self.driver_profile,
            status=Delivery.Status.ASSIGNED,
        )

        self.order2 = Order.objects.create(
            order_number="ORD-P5-0002",
            customer=self.customer2,
            route=self.route_pandikkad,
            driver=self.driver_profile,
            total_amount=Decimal("300.00"),
            order_date=timezone.now().date(),
            status=Order.Status.CONFIRMED,
        )
        OrderItem.objects.create(order=self.order2, product=self.kubbus, quantity=30, unit_price=Decimal("10.00"), subtotal=Decimal("300.00"))
        self.delivery2 = Delivery.objects.create(
            delivery_number="DEL-P5-0002",
            order=self.order2,
            route=self.route_pandikkad,
            driver=self.driver_profile,
            status=Delivery.Status.ASSIGNED,
        )

        # Delivery for other driver
        self.other_order = Order.objects.create(
            order_number="ORD-P5-0003",
            customer=self.other_route_customer,
            route=self.route_melattur,
            driver=self.driver_other_profile,
            total_amount=Decimal("400.00"),
            order_date=timezone.now().date(),
            status=Order.Status.CONFIRMED,
        )
        self.other_delivery = Delivery.objects.create(
            delivery_number="DEL-P5-0003",
            order=self.other_order,
            route=self.route_melattur,
            driver=self.driver_other_profile,
            status=Delivery.Status.ASSIGNED,
        )

    def test_driver_login_and_dashboard_summary(self):
        """Driver logs in and views their route dashboard summary."""
        self.client.force_authenticate(user=self.driver_user)
        response = self.client.get("/api/v1/reports/dashboard/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data["route_name"], "Pandikkad Route")
        self.assertEqual(data["vehicle_number"], "KL-53-E-1001")
        self.assertIn("completed_deliveries", data)
        self.assertIn("not_delivered_count", data)

    def test_driver_deliveries_list_isolated_to_driver(self):
        """Driver only receives deliveries assigned to them."""
        self.client.force_authenticate(user=self.driver_user)
        response = self.client.get("/api/v1/deliveries/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        delivery_ids = [d["id"] for d in (response.data if isinstance(response.data, list) else response.data["results"])]
        
        self.assertIn(str(self.delivery1.id), delivery_ids)
        self.assertIn(str(self.delivery2.id), delivery_ids)
        # Cannot see other driver's delivery
        self.assertNotIn(str(self.other_delivery.id), delivery_ids)

    def test_driver_complete_delivery_flow(self):
        """Driver completes delivery with recipient name and remarks."""
        self.client.force_authenticate(user=self.driver_user)
        response = self.client.post(
            f"/api/v1/deliveries/{self.delivery1.id}/complete/",
            {"recipient_name": "Moideen (Owner)", "notes": "Supplied 50 fresh Kubbus packets"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.delivery1.refresh_from_db()
        self.assertEqual(self.delivery1.status, Delivery.Status.DELIVERED)
        self.assertEqual(self.delivery1.recipient_name, "Moideen (Owner)")
        self.assertIsNotNone(self.delivery1.delivered_at)

        # Order status also updated to DELIVERED
        self.order1.refresh_from_db()
        self.assertEqual(self.order1.status, Order.Status.DELIVERED)

    def test_driver_mark_not_delivered_requires_reason(self):
        """Driver marks delivery as not delivered; blank reason is rejected."""
        self.client.force_authenticate(user=self.driver_user)
        
        # 1. Blank reason should fail
        response_blank = self.client.post(
            f"/api/v1/deliveries/{self.delivery2.id}/mark-not-delivered/",
            {"failed_reason": "   ", "notes": "No reason provided"}
        )
        self.assertEqual(response_blank.status_code, status.HTTP_400_BAD_REQUEST)

        # 2. Valid reason succeeds and logs activity
        response_valid = self.client.post(
            f"/api/v1/deliveries/{self.delivery2.id}/mark-not-delivered/",
            {"failed_reason": "Shop Closed", "notes": "Morning shutter down, phone not reachable"}
        )
        self.assertEqual(response_valid.status_code, status.HTTP_200_OK)

        self.delivery2.refresh_from_db()
        self.assertEqual(self.delivery2.status, Delivery.Status.NOT_DELIVERED)
        self.assertEqual(self.delivery2.failed_reason, "Shop Closed")

        # Verify activity history recorded
        activity = ActivityLog.objects.filter(entity_id=self.delivery2.id, action="NOT_DELIVERED").first()
        self.assertIsNotNone(activity)
        self.assertIn("Shop Closed", activity.summary)

    def test_driver_payment_collection_cash_and_upi(self):
        """Driver collects Cash for order and GPay/UPI for credit."""
        self.client.force_authenticate(user=self.driver_user)

        # 1. Collect Cash for Order #1
        resp1 = self.client.post(
            "/api/v1/payments/",
            {
                "customer_id": str(self.customer1.id),
                "order_id": str(self.order1.id),
                "amount": "500.00",
                "payment_method": "CASH",
                "notes": "Collected cash at delivery",
            }
        )
        self.assertEqual(resp1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp1.data["payment_method"], "CASH")
        self.assertEqual(resp1.data["payment_type"], "ORDER_PAYMENT")

        # 2. Collect UPI for Previous Credit
        resp2 = self.client.post(
            "/api/v1/payments/",
            {
                "customer_id": str(self.customer2.id),
                "amount": "1000.00",
                "payment_method": "GPAY_UPI",
                "reference_number": "UPI-88990011",
                "notes": "GPay previous balance settlement",
            }
        )
        self.assertEqual(resp2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp2.data["payment_method"], "GPAY_UPI")
        self.assertEqual(resp2.data["payment_type"], "PREVIOUS_CREDIT")

        # Check reconciliation summary
        summary_resp = self.client.get("/api/v1/payments/daily-summary/")
        self.assertEqual(summary_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(summary_resp.data["cash_total"]), Decimal("500.00"))
        self.assertEqual(Decimal(summary_resp.data["upi_total"]), Decimal("1000.00"))
        self.assertEqual(Decimal(summary_resp.data["total_collected"]), Decimal("1500.00"))

    def test_driver_expenses_creation_and_reconciliation(self):
        """Driver logs expenses and reconciles net collection handover."""
        self.client.force_authenticate(user=self.driver_user)

        # Log Petrol expense
        resp_exp = self.client.post(
            "/api/v1/driver-expenses/",
            {
                "category": "PETROL",
                "amount": "300.00",
                "date": str(timezone.now().date()),
                "notes": "Diesel for delivery van",
            }
        )
        self.assertEqual(resp_exp.status_code, status.HTTP_201_CREATED)

        # Driver summary should reflect expense
        exp_summary_resp = self.client.get("/api/v1/driver-expenses/summary/")
        self.assertEqual(exp_summary_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(exp_summary_resp.data["today_total"]), Decimal("300.00"))

    def test_driver_cannot_access_other_driver_delivery_or_expense(self):
        """Security audit: Driver A cannot complete Driver B's delivery or view their expenses."""
        self.client.force_authenticate(user=self.driver_user)

        # Attempt to complete Driver B's delivery
        bad_complete = self.client.post(
            f"/api/v1/deliveries/{self.other_delivery.id}/complete/",
            {"recipient_name": "Hacked Staff"}
        )
        self.assertIn(bad_complete.status_code, [status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN])

        # Attempt to create expense for another driver
        DriverExpense.objects.create(
            driver=self.driver_other_profile,
            category=DriverExpense.Category.FOOD,
            amount=Decimal("150.00"),
            date=timezone.now().date(),
        )
        other_expenses = self.client.get("/api/v1/driver-expenses/")
        for exp in (other_expenses.data if isinstance(other_expenses.data, list) else other_expenses.data["results"]):
            self.assertEqual(exp["driver"], str(self.driver_profile.id))
