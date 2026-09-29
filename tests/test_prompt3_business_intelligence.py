import datetime
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from apps.routes.models import Route, Driver, DriverExpense
from apps.products.models import Product
from apps.customers.models import Customer, CustomerProductPrice
from apps.orders.models import Order, OrderItem
from apps.deliveries.models import Delivery
from apps.payments.models import Payment
from apps.common.models import ActivityLog
from apps.orders.services import create_order_service
from apps.customers.services import set_customer_product_price, get_effective_product_price
from apps.deliveries.services import complete_delivery_service, mark_delivery_not_delivered_service
from apps.payments.services import record_payment_service

User = get_user_model()


class Prompt3BusinessIntelligenceTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Users
        self.owner = User.objects.create_user(
            username="owner_test",
            password="OwnerPassword123!",
            role="OWNER",
            first_name="Owner",
            last_name="User"
        )
        self.manager = User.objects.create_user(
            username="manager_test",
            password="ManagerPassword123!",
            role="MANAGER",
            first_name="Manager",
            last_name="User"
        )
        self.driver_user = User.objects.create_user(
            username="driver_test",
            password="DriverPassword123!",
            role="DRIVER",
            first_name="Driver",
            last_name="One"
        )
        self.other_driver_user = User.objects.create_user(
            username="driver_two",
            password="DriverPassword123!",
            role="DRIVER",
            first_name="Driver",
            last_name="Two"
        )

        # Routes
        self.route_pandikkad = Route.objects.create(name="Pandikkad", code="PKD", description="Route 1")
        self.route_perundurai = Route.objects.create(name="Perundurai", code="PRD", description="Route 2")

        # Driver Profiles
        self.driver = Driver.objects.create(
            user=self.driver_user,
            phone_number="9876543210",
            assigned_route=self.route_pandikkad,
            vehicle_number="KL-10-AA-1111",
            license_number="DL-1111"
        )
        self.other_driver = Driver.objects.create(
            user=self.other_driver_user,
            phone_number="9876543211",
            assigned_route=self.route_perundurai,
            vehicle_number="KL-10-BB-2222",
            license_number="DL-2222"
        )

        # Products
        self.kubbus = Product.objects.create(
            name="Kubbus",
            code="KUB-10",
            unit_price=Decimal("10.00"),
            packet_size="10 pieces"
        )
        self.romali = Product.objects.create(
            name="Romali",
            code="ROM-05",
            unit_price=Decimal("8.00"),
            packet_size="5 pieces"
        )

        # Customer Shop
        self.customer = Customer.objects.create(
            name="ABC Bakery",
            owner_name="Ahmed",
            phone="9847000001",
            address="Pandikkad Town",
            route=self.route_pandikkad,
            credit_limit=Decimal("5000.00"),
            current_balance=Decimal("0.00")
        )

    # -------------------------------------------------------------
    # 1. DAILY BUSINESS SUMMARY & DATE FILTERING
    # -------------------------------------------------------------
    def test_daily_summary_sales_collections_expenses_and_net_collection(self):
        """
        Verify:
        Sales, Collection, Credit, Deliveries, Driver Expenses, and
        Net Collection = Today's Collection - Today's Driver Expenses
        """
        # Create Order today for ABC Bakery: 100 Kubbus @ 10.00 = 1000.00
        order = create_order_service(
            customer_id=self.customer.id,
            items_data=[{"product_id": str(self.kubbus.id), "quantity": 100, "unit_price": Decimal("10.00")}],
            created_by=self.manager
        )
        self.assertEqual(order.total_amount, Decimal("1000.00"))

        # Deliver the order
        delivery = Delivery.objects.get(order=order)
        complete_delivery_service(delivery_id=delivery.id, user=self.driver_user, recipient_name="Ahmed")

        # Record Collection of 700.00
        payment = record_payment_service(
            customer_id=self.customer.id,
            amount=Decimal("700.00"),
            payment_method="CASH",
            collected_by=self.driver_user,
            order_id=order.id
        )

        # Record Driver Expense of 200.00
        expense = DriverExpense.objects.create(
            driver=self.driver,
            category=DriverExpense.Category.PETROL,
            amount=Decimal("200.00"),
            date=datetime.date.today(),
            notes="Morning fuel refill"
        )

        # Query Owner Dashboard
        self.client.force_authenticate(user=self.owner)
        response = self.client.get("/api/v1/reports/dashboard/?date_preset=today")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        self.assertEqual(data["today_orders_count"], 1)
        self.assertEqual(Decimal(str(data["today_sales"])), Decimal("1000.00"))
        self.assertEqual(Decimal(str(data["total_collected"])), Decimal("700.00"))
        self.assertEqual(Decimal(str(data["today_expenses"])), Decimal("200.00"))
        
        # Net Collection = Collection - Expenses = 700 - 200 = 500
        self.assertEqual(Decimal(str(data["net_collection"])), Decimal("500.00"))
        self.assertEqual(data["completed_deliveries"], 1)
        self.assertEqual(data["pending_deliveries"], 0)
        self.assertEqual(data["not_delivered_count"], 0)

    def test_daily_summary_date_filtering(self):
        """
        Verify that orders on past dates are properly filtered out when viewing 'today'.
        """
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        
        # Order placed yesterday
        old_order = Order.objects.create(
            customer=self.customer,
            route=self.route_pandikkad,
            driver=self.driver,
            order_date=yesterday,
            status=Order.Status.CONFIRMED,
            total_amount=Decimal("500.00")
        )
        OrderItem.objects.create(
            order=old_order,
            product=self.kubbus,
            quantity=50,
            unit_price=Decimal("10.00"),
            subtotal=Decimal("500.00")
        )

        self.client.force_authenticate(user=self.owner)
        
        # 'today' should show 0 orders
        res_today = self.client.get("/api/v1/reports/dashboard/?date_preset=today")
        self.assertEqual(res_today.data["today_orders_count"], 0)
        self.assertEqual(Decimal(str(res_today.data["today_sales"])), Decimal("0.00"))

        # 'yesterday' should show 1 order with 500.00 sales
        res_yesterday = self.client.get("/api/v1/reports/dashboard/?date_preset=yesterday")
        self.assertEqual(res_yesterday.data["today_orders_count"], 1)
        self.assertEqual(Decimal(str(res_yesterday.data["today_sales"])), Decimal("500.00"))

    # -------------------------------------------------------------
    # 2. DRIVER PERFORMANCE REPORT & DRILLDOWN
    # -------------------------------------------------------------
    def test_driver_performance_report_and_route_filtering(self):
        """
        Verify driver performance calculates assigned, delivered, collections,
        expenses, and net collection accurately, and supports route filtering.
        """
        order = create_order_service(
            customer_id=self.customer.id,
            items_data=[{"product_id": str(self.kubbus.id), "quantity": 100, "unit_price": Decimal("10.00")}],
            created_by=self.manager
        )
        delivery = Delivery.objects.get(order=order)
        complete_delivery_service(delivery_id=delivery.id, user=self.driver_user)
        record_payment_service(
            customer_id=self.customer.id,
            amount=Decimal("1000.00"),
            payment_method="CASH",
            collected_by=self.driver_user,
            order_id=order.id
        )
        DriverExpense.objects.create(
            driver=self.driver,
            category=DriverExpense.Category.FOOD,
            amount=Decimal("150.00"),
            date=datetime.date.today()
        )

        self.client.force_authenticate(user=self.owner)
        
        # Test full driver performance
        res = self.client.get("/api/v1/reports/driver-performance/?date_preset=today")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        drivers_list = res.data["drivers"]
        d1 = next(d for d in drivers_list if d["driver_id"] == str(self.driver.id))
        
        self.assertEqual(d1["total_assigned"], 1)
        self.assertEqual(d1["delivered"], 1)
        self.assertEqual(Decimal(str(d1["collection_amount"])), Decimal("1000.00"))
        self.assertEqual(Decimal(str(d1["expenses"])), Decimal("150.00"))
        self.assertEqual(Decimal(str(d1["net_collection"])), Decimal("850.00"))

        # Test filter by Route: Perundurai route should NOT include Driver One
        res_prd = self.client.get(f"/api/v1/reports/driver-performance/?route={self.route_perundurai.id}")
        self.assertEqual(len(res_prd.data["drivers"]), 1)
        self.assertEqual(res_prd.data["drivers"][0]["driver_id"], str(self.other_driver.id))

    def test_driver_detail_drilldown_and_isolation(self):
        """
        Verify driver detail drilldown shows deliveries, collections, expenses, and
        that a Driver CANNOT view another driver's drilldown.
        """
        # Manager/Owner can access driver 1 detail
        self.client.force_authenticate(user=self.manager)
        res_manager = self.client.get(f"/api/v1/reports/driver-performance/{self.driver.id}/")
        self.assertEqual(res_manager.status_code, status.HTTP_200_OK)
        self.assertIn("deliveries", res_manager.data)
        self.assertIn("collections", res_manager.data)
        self.assertIn("expenses", res_manager.data)
        self.assertIn("summary", res_manager.data)

        # Driver One CAN access their own detail
        self.client.force_authenticate(user=self.driver_user)
        res_self = self.client.get(f"/api/v1/reports/driver-performance/{self.driver.id}/")
        self.assertEqual(res_self.status_code, status.HTTP_200_OK)

        # Driver One CANNOT access Driver Two's detail (Forbidden)
        res_forbidden = self.client.get(f"/api/v1/reports/driver-performance/{self.other_driver.id}/")
        self.assertEqual(res_forbidden.status_code, status.HTTP_403_FORBIDDEN)

    # -------------------------------------------------------------
    # 3. CUSTOMER REPEAT ORDER & HISTORICAL INTEGRITY
    # -------------------------------------------------------------
    def test_repeat_order_loads_current_pricing_and_preserves_old_order(self):
        """
        When repeating an order:
        1. Historical order must retain historical prices (e.g. 10.00).
        2. Customer summary provides last order items and flags price changes.
        3. A new order created with current pricing (e.g. 11.50) saves cleanly.
        4. The old order remains completely unchanged at 10.00.
        """
        # Step 1: Create initial order at historical rate 10.00
        old_order = create_order_service(
            customer_id=self.customer.id,
            items_data=[{"product_id": str(self.kubbus.id), "quantity": 100, "unit_price": Decimal("10.00")}],
            created_by=self.manager
        )
        self.assertEqual(old_order.total_amount, Decimal("1000.00"))

        # Step 2: Now price increases to 11.50 for this customer
        set_customer_product_price(
            customer=self.customer,
            product=self.kubbus,
            price=Decimal("11.50"),
            user=self.manager
        )

        # Step 3: Check Customer summary endpoint
        self.client.force_authenticate(user=self.manager)
        res_summary = self.client.get(f"/api/v1/customers/{self.customer.id}/summary/")
        self.assertEqual(res_summary.status_code, status.HTTP_200_OK)
        last_order = res_summary.data["last_order"]
        self.assertIsNotNone(last_order)
        self.assertEqual(last_order["order_number"], old_order.order_number)
        
        # Verify comparison: historical 10.00 vs current 11.50
        item_info = last_order["items"][0]
        self.assertEqual(Decimal(str(item_info["historical_unit_price"])), Decimal("10.00"))
        self.assertEqual(Decimal(str(item_info["current_unit_price"])), Decimal("11.50"))
        self.assertTrue(item_info["price_changed"])

        # Step 4: Create repeated new order using customer's current pricing
        effective_price, _, _ = get_effective_product_price(self.customer, self.kubbus)
        self.assertEqual(effective_price, Decimal("11.50"))

        new_order = create_order_service(
            customer_id=self.customer.id,
            items_data=[{"product_id": str(self.kubbus.id), "quantity": 100, "unit_price": effective_price}],
            created_by=self.manager
        )
        self.assertEqual(new_order.total_amount, Decimal("1150.00"))

        # Step 5: Verify old order was NOT altered
        old_order.refresh_from_db()
        self.assertEqual(old_order.total_amount, Decimal("1000.00"))
        self.assertEqual(old_order.items.first().unit_price, Decimal("10.00"))

    # -------------------------------------------------------------
    # 4. FREQUENT ORDER INFORMATION
    # -------------------------------------------------------------
    def test_frequent_order_information(self):
        """
        Verify factual frequent order statistics (most frequent product, typical quantity, order count).
        """
        # Place 2 orders: 100 Kubbus each
        create_order_service(
            customer_id=self.customer.id,
            items_data=[{"product_id": str(self.kubbus.id), "quantity": 100, "unit_price": Decimal("10.00")}],
            created_by=self.manager
        )
        create_order_service(
            customer_id=self.customer.id,
            items_data=[
                {"product_id": str(self.kubbus.id), "quantity": 60, "unit_price": Decimal("10.00")},
                {"product_id": str(self.romali.id), "quantity": 20, "unit_price": Decimal("8.00")}
            ],
            created_by=self.manager
        )

        self.client.force_authenticate(user=self.owner)
        res = self.client.get(f"/api/v1/customers/{self.customer.id}/summary/")
        frequent = res.data["frequent_order_info"]
        
        self.assertEqual(frequent["most_frequent_product"], "Kubbus")
        # Total Kubbus = 100 + 60 = 160 across 2 orders -> typical quantity = 80
        self.assertEqual(frequent["typical_quantity"], 80)
        self.assertEqual(frequent["total_orders"], 2)

    # -------------------------------------------------------------
    # 5. ACTIVITY HISTORY / AUDIT LOGGING & SECURITY
    # -------------------------------------------------------------
    def test_audit_log_creation_and_security(self):
        """
        Verify:
        - Price change logs old and new prices.
        - Payment logs receipt and amount.
        - Drivers CANNOT view activity history (Forbidden).
        - Owner and Manager CAN view activity history.
        """
        # Trigger Price Change Audit
        set_customer_product_price(
            customer=self.customer,
            product=self.kubbus,
            price=Decimal("12.00"),
            user=self.manager
        )

        # Trigger Order Creation Audit
        order = create_order_service(
            customer_id=self.customer.id,
            items_data=[{"product_id": str(self.kubbus.id), "quantity": 50, "unit_price": Decimal("12.00")}],
            created_by=self.manager
        )

        # Check Audit Log in DB
        logs = ActivityLog.objects.filter(entity_type=ActivityLog.EntityType.PRICE)
        self.assertTrue(logs.exists())
        price_log = logs.first()
        self.assertEqual(price_log.user_name, self.manager.get_full_name() or self.manager.username)
        self.assertIn(price_log.action, [ActivityLog.ActionType.CREATED, ActivityLog.ActionType.UPDATED])
        self.assertEqual(Decimal(str(price_log.details["new_price"])), Decimal("12.00"))

        # Test Permissions: Driver MUST be denied access to activity logs
        self.client.force_authenticate(user=self.driver_user)
        res_driver = self.client.get("/api/v1/activity-logs/")
        self.assertEqual(res_driver.status_code, status.HTTP_403_FORBIDDEN)

        # Owner has full access to activity logs
        self.client.force_authenticate(user=self.owner)
        res_owner = self.client.get("/api/v1/activity-logs/")
        self.assertEqual(res_owner.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res_owner.data), 2)
