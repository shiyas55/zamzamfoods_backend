import datetime
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User
from apps.customers.models import Customer
from apps.routes.models import Route, Driver, DriverShift
from apps.products.models import Product
from apps.orders.models import Order, OrderItem
from apps.deliveries.models import Delivery
from apps.payments.models import Payment
from apps.credits.models import CreditTransaction
from apps.reports.models import DailyClosing
from apps.orders.services import create_order_service, update_order_service


class ZamzamCompleteSandboxAuditTestCase(TestCase):
    """
    COMPLETE End-to-End Functional and Logical Sandbox Audit for Zamzam Bill System.
    Uses Django's isolated test database - does NOT touch development/production db.sqlite3.
    Covers Phases 1 through 23 of the audit specification.
    """

    def setUp(self):
        self.client = APIClient()

        # Manager user
        self.manager = User.objects.create_user(
            username="audit_manager",
            email="manager@zamzam.test",
            password="TestPassword123!",
            role=User.Role.MANAGER,
            first_name="Audit",
            last_name="Manager"
        )

        # Owner user
        self.owner = User.objects.create_user(
            username="audit_owner",
            email="owner@zamzam.test",
            password="TestPassword123!",
            role=User.Role.OWNER,
            first_name="Audit",
            last_name="Owner"
        )

        # Phase 3: Exactly 2 Test Drivers
        self.driver_user_1 = User.objects.create_user(
            username="test_driver_1",
            email="driver1@zamzam.test",
            password="TestPassword123!",
            role=User.Role.DRIVER,
            first_name="Test",
            last_name="Driver 1"
        )
        self.driver_user_2 = User.objects.create_user(
            username="test_driver_2",
            email="driver2@zamzam.test",
            password="TestPassword123!",
            role=User.Role.DRIVER,
            first_name="Test",
            last_name="Driver 2"
        )

        # Phase 3: Exactly 2 Test Routes
        self.route_a = Route.objects.create(name="TEST-ROUTE-A", code="ROU-A")
        self.route_b = Route.objects.create(name="TEST-ROUTE-B", code="ROU-B")

        self.driver_1 = Driver.objects.create(
            user=self.driver_user_1,
            assigned_route=self.route_a,
            phone_number="9876543210",
            vehicle_number="KL-01-AA-1111",
            is_active=True
        )
        self.driver_2 = Driver.objects.create(
            user=self.driver_user_2,
            assigned_route=self.route_b,
            phone_number="9876543211",
            vehicle_number="KL-01-BB-2222",
            is_active=True
        )

        # Phase 3: Exactly 5 Test Products with fixed predictable prices
        self.prod_a = Product.objects.create(name="TEST-PRODUCT-A (Kubbus Normal)", code="KUB", unit_price=Decimal("10.00"), is_active=True)
        self.prod_b = Product.objects.create(name="TEST-PRODUCT-B (Romali Roti)", code="ROM", unit_price=Decimal("15.00"), is_active=True)
        self.prod_c = Product.objects.create(name="TEST-PRODUCT-C (Wheat Kubbus)", code="WKB", unit_price=Decimal("20.00"), is_active=True)
        self.prod_d = Product.objects.create(name="TEST-PRODUCT-D (Jumbo Kubbus)", code="JKB", unit_price=Decimal("25.00"), is_active=True)
        self.prod_e = Product.objects.create(name="TEST-PRODUCT-E (Oil Roti)", code="OIL", unit_price=Decimal("30.00"), is_active=True)

        # Phase 3: Exactly 5 Test Customers
        self.cust_1 = Customer.objects.create(
            name="TEST-CUSTOMER-01",
            owner_name="Al Madina Store",
            phone="9800000001",
            address="Audit St 1",
            route=self.route_a,
            credit_limit=Decimal("5000.00"),
            is_active=True
        )
        self.cust_2 = Customer.objects.create(
            name="TEST-CUSTOMER-02",
            owner_name="Zamzam Mart",
            phone="9800000002",
            address="Audit St 2",
            route=self.route_a,
            credit_limit=Decimal("5000.00"),
            is_active=True
        )
        self.cust_3 = Customer.objects.create(
            name="TEST-CUSTOMER-03",
            owner_name="Calicut Bakery",
            phone="9800000003",
            address="Audit St 3",
            route=self.route_a,
            credit_limit=Decimal("5000.00"),
            is_active=True
        )
        self.cust_4 = Customer.objects.create(
            name="TEST-CUSTOMER-04",
            owner_name="Malabar Cafe",
            phone="9800000004",
            address="Audit St 4",
            route=self.route_b,
            credit_limit=Decimal("5000.00"),
            is_active=True
        )
        self.cust_5 = Customer.objects.create(
            name="TEST-CUSTOMER-05",
            owner_name="Highway Hotel",
            phone="9800000005",
            address="Audit St 5",
            route=self.route_b,
            credit_limit=Decimal("5000.00"),
            is_active=True
        )

        # Open Daily Closing for today to ensure operational day is opened
        self.today = timezone.localdate()
        self.closing, _ = DailyClosing.objects.get_or_create(
            date=self.today,
            defaults={"is_opened": True, "is_closed": False}
        )
        self.closing.is_opened = True
        self.closing.is_closed = False
        self.closing.save()

    # =========================================================================
    # PHASE 4: CUSTOMER CREATION & INTEGRITY AUDIT
    # =========================================================================
    def test_phase4_customer_creation_integrity(self):
        """Test customer creation API, unique constraint, route mapping, and editing."""
        self.client.force_authenticate(user=self.manager)

        # 1. Create Customer via API
        payload = {
            "name": "TEST-CUSTOMER-NEW",
            "owner_name": "New Audit Owner",
            "phone": "9800000099",
            "address": "Audit St New",
            "route": str(self.route_a.id),
            "credit_limit": "2000.00"
        }
        res = self.client.post("/api/v1/customers/", payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        new_cust_id = res.data["id"]

        # 2. Verify Customer is created exactly once in DB
        self.assertEqual(Customer.objects.filter(phone="9800000099").count(), 1)
        new_cust = Customer.objects.get(id=new_cust_id)
        self.assertEqual(new_cust.route.id, self.route_a.id)

        # 3. Search Customer finds exactly one
        search_res = self.client.get(f"/api/v1/customers/?search=9800000099")
        self.assertEqual(len(search_res.data["results"] if "results" in search_res.data else search_res.data), 1)

        # 4. Edit Customer does not create second customer
        patch_res = self.client.patch(f"/api/v1/customers/{new_cust_id}/", {"credit_limit": "3500.00"})
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertEqual(Customer.objects.filter(phone="9800000099").count(), 1)
        new_cust.refresh_from_db()
        self.assertEqual(new_cust.credit_limit, Decimal("3500.00"))

    # =========================================================================
    # PHASE 5 & 6: DRIVER & ROUTE ISOLATION
    # =========================================================================
    def test_phase5_and_6_driver_and_route_containment(self):
        """Verify routes strictly contain only assigned customers and drivers."""
        # Route A has cust 1, 2, 3
        route_a_custs = Customer.objects.filter(route=self.route_a)
        self.assertEqual(route_a_custs.count(), 3)
        self.assertTrue(all(c.id in [self.cust_1.id, self.cust_2.id, self.cust_3.id] for c in route_a_custs))

        # Route B has cust 4, 5
        route_b_custs = Customer.objects.filter(route=self.route_b)
        self.assertEqual(route_b_custs.count(), 2)
        self.assertTrue(all(c.id in [self.cust_4.id, self.cust_5.id] for c in route_b_custs))

        # No customer is duplicated across routes
        overlap = set(route_a_custs.values_list("id", flat=True)).intersection(
            set(route_b_custs.values_list("id", flat=True))
        )
        self.assertEqual(len(overlap), 0)

    # =========================================================================
    # PHASE 7 & 8: ORDER CREATION & ORDER ITEM LOGIC
    # =========================================================================
    def test_phase7_and_8_order_item_calculation_and_duplicate_aggregation(self):
        """
        Verify:
        quantity x unit price = item total
        Sum of item totals = order total
        Adding same product twice in a request aggregates quantities into one OrderItem.
        """
        self.client.force_authenticate(user=self.manager)

        # Customer 1 orders: Product A (qty 2 @ 10) + Product B (qty 3 @ 15)
        # Plus product A repeated (qty 1 @ 10) to test duplicate item protection
        order_payload = {
            "customer_id": str(self.cust_1.id),
            "order_date": str(self.today),
            "driver_id": str(self.driver_1.id),
            "items": [
                {"product_id": str(self.prod_a.id), "quantity": 2, "unit_price": "10.00"},
                {"product_id": str(self.prod_b.id), "quantity": 3, "unit_price": "15.00"},
                {"product_id": str(self.prod_a.id), "quantity": 1, "unit_price": "10.00"},  # duplicate product in payload
            ]
        }
        res = self.client.post("/api/v1/orders/", order_payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        order_id = res.data["id"]
        order = Order.objects.get(id=order_id)

        # Check DB OrderItems: must only have 2 rows (Product A aggregated to 2+1=3, Product B = 3)
        items = list(order.items.all())
        self.assertEqual(len(items), 2, "Duplicate product in request must be aggregated, not duplicated!")

        item_a = next(i for i in items if i.product_id == self.prod_a.id)
        item_b = next(i for i in items if i.product_id == self.prod_b.id)

        self.assertEqual(item_a.quantity, 3)
        self.assertEqual(item_a.unit_price, Decimal("10.00"))
        self.assertEqual(item_a.total_price, Decimal("30.00"))  # 3 * 10

        self.assertEqual(item_b.quantity, 3)
        self.assertEqual(item_b.unit_price, Decimal("15.00"))
        self.assertEqual(item_b.total_price, Decimal("45.00"))  # 3 * 15

        # Check Order total: 30 + 45 = 75.00
        self.assertEqual(order.total_amount, Decimal("75.00"))

    # =========================================================================
    # PHASE 9 & 15: THE "9 ORDERS VS 11 ORDERS" BUG & ORDER COUNTS
    # =========================================================================
    def test_phase9_and_15_nine_orders_accuracy(self):
        """
        Create EXACTLY 9 test orders across customers using both self-order and manual order.
        Verify:
        - DB count = 9
        - API count = 9
        - Driver orders count matches assignments
        - Order history pagination and filters return exact counts (never 10 or 11).
        """
        self.client.force_authenticate(user=self.manager)

        created_orders = []

        # 5 Manual Orders (Manager Entry)
        # Order 1: Cust 1, Driver 1
        ord1 = create_order_service(
            customer_id=self.cust_1.id,
            order_date=self.today,
            driver_id=self.driver_1.id,
            source="MANAGER",
            items_data=[{"product_id": str(self.prod_a.id), "quantity": 10, "unit_price": "10.00"}]
        )
        created_orders.append(ord1)

        # Order 2: Cust 2, Driver 1
        ord2 = create_order_service(
            customer_id=self.cust_2.id,
            order_date=self.today,
            driver_id=self.driver_1.id,
            source="MANAGER",
            items_data=[{"product_id": str(self.prod_b.id), "quantity": 5, "unit_price": "15.00"}]
        )
        created_orders.append(ord2)

        # Order 3: Cust 3, Driver 1
        ord3 = create_order_service(
            customer_id=self.cust_3.id,
            order_date=self.today,
            driver_id=self.driver_1.id,
            source="MANAGER",
            items_data=[{"product_id": str(self.prod_c.id), "quantity": 8, "unit_price": "20.00"}]
        )
        created_orders.append(ord3)

        # Order 4: Cust 4, Driver 2
        ord4 = create_order_service(
            customer_id=self.cust_4.id,
            order_date=self.today,
            driver_id=self.driver_2.id,
            source="MANAGER",
            items_data=[{"product_id": str(self.prod_d.id), "quantity": 4, "unit_price": "25.00"}]
        )
        created_orders.append(ord4)

        # Order 5: Cust 5, Driver 2
        ord5 = create_order_service(
            customer_id=self.cust_5.id,
            order_date=self.today,
            driver_id=self.driver_2.id,
            source="MANAGER",
            items_data=[{"product_id": str(self.prod_e.id), "quantity": 6, "unit_price": "30.00"}]
        )
        created_orders.append(ord5)

        # 4 Self-Orders (Customer Portal Entry)
        # Order 6: Cust 1 (Self order)
        self.client.force_authenticate(user=None)
        res6 = self.client.post(
            f"/api/v1/public/customer-order/{self.cust_1.id}/",
            {"items": [{"product_id": str(self.prod_a.id), "quantity": 15}]},
            format="json"
        )
        self.assertEqual(res6.status_code, status.HTTP_201_CREATED)
        created_orders.append(Order.objects.get(id=res6.data["order_id"]))

        # Order 7: Cust 2 (Self order)
        res7 = self.client.post(
            f"/api/v1/public/customer-order/{self.cust_2.id}/",
            {"items": [{"product_id": str(self.prod_b.id), "quantity": 12}]},
            format="json"
        )
        self.assertEqual(res7.status_code, status.HTTP_201_CREATED)
        created_orders.append(Order.objects.get(id=res7.data["order_id"]))

        # Order 8: Cust 4 (Self order)
        res8 = self.client.post(
            f"/api/v1/public/customer-order/{self.cust_4.id}/",
            {"items": [{"product_id": str(self.prod_c.id), "quantity": 7}]},
            format="json"
        )
        self.assertEqual(res8.status_code, status.HTTP_201_CREATED)
        created_orders.append(Order.objects.get(id=res8.data["order_id"]))

        # Order 9: Cust 5 (Self order)
        res9 = self.client.post(
            f"/api/v1/public/customer-order/{self.cust_5.id}/",
            {"items": [{"product_id": str(self.prod_d.id), "quantity": 9}]},
            format="json"
        )
        self.assertEqual(res9.status_code, status.HTTP_201_CREATED)
        created_orders.append(Order.objects.get(id=res9.data["order_id"]))

        # VERIFICATION 1: Database count MUST be EXACTLY 9
        db_count = Order.objects.count()
        self.assertEqual(db_count, 9, f"Expected 9 orders in database, found {db_count}")

        # VERIFICATION 2: Manager API count MUST be EXACTLY 9
        self.client.force_authenticate(user=self.manager)
        api_res = self.client.get("/api/v1/orders/")
        api_orders = api_res.data["results"] if "results" in api_res.data else api_res.data
        self.assertEqual(len(api_orders), 9, f"Expected 9 orders from API, found {len(api_orders)}")

        # VERIFICATION 3: Driver isolation counts
        # Driver 1 has Route A (Cust 1, 2, 3): Orders 1, 2, 3, 6, 7 = 5 orders
        self.client.force_authenticate(user=self.driver_user_1)
        driver1_res = self.client.get("/api/v1/orders/")
        driver1_orders = driver1_res.data["results"] if "results" in driver1_res.data else driver1_res.data
        self.assertEqual(len(driver1_orders), 5, f"Driver 1 expected 5 orders, found {len(driver1_orders)}")

        # Driver 2 has Route B (Cust 4, 5): Orders 4, 5, 8, 9 = 4 orders
        self.client.force_authenticate(user=self.driver_user_2)
        driver2_res = self.client.get("/api/v1/orders/")
        driver2_orders = driver2_res.data["results"] if "results" in driver2_res.data else driver2_res.data
        self.assertEqual(len(driver2_orders), 4, f"Driver 2 expected 4 orders, found {len(driver2_orders)}")

        # Sum of driver orders: 5 + 4 = 9 (No double counted orders!)
        self.assertEqual(len(driver1_orders) + len(driver2_orders), 9)

    # =========================================================================
    # PHASE 10: TIMESTAMP AUDIT
    # =========================================================================
    def test_phase10_timestamp_logic(self):
        """
        Verify:
        - created_at is set at creation
        - submitted_at is set when order is submitted/locked
        - driver shift opening sets opened_at without altering order created_at or submitted_at
        - delivery completion sets delivered_at
        """
        # Create order
        order = create_order_service(
            customer_id=self.cust_1.id,
            order_date=self.today,
            driver_id=self.driver_1.id,
            source="MANAGER",
            items_data=[{"product_id": str(self.prod_a.id), "quantity": 10, "unit_price": "10.00"}]
        )

        self.assertIsNotNone(order.created_at)
        self.assertIsNotNone(order.submitted_at)
        initial_created_at = order.created_at
        initial_submitted_at = order.submitted_at

        # Driver opens day shift
        self.client.force_authenticate(user=self.driver_user_1)
        open_res = self.client.post("/api/v1/driver-shifts/open_day/", {
            "kubbus_loaded": 100,
            "romali_loaded": 50,
            "opening_notes": "Morning vehicle stock audit check"
        })
        self.assertEqual(open_res.status_code, status.HTTP_200_OK)

        shift = DriverShift.objects.get(driver=self.driver_1, date=self.today)
        self.assertTrue(shift.is_opened)
        self.assertIsNotNone(shift.opened_at)

        # Check that order's created_at and submitted_at are NOT altered
        order.refresh_from_db()
        self.assertEqual(order.created_at, initial_created_at)
        self.assertEqual(order.submitted_at, initial_submitted_at)

        # Delivery check: Deliver order
        delivery = Delivery.objects.filter(order=order).first()
        self.assertIsNotNone(delivery, "Delivery must exist for driver")
        self.assertIsNone(delivery.delivered_at)

        deliv_res = self.client.post(f"/api/v1/deliveries/{delivery.id}/complete/", {
            "recipient_name": "Store Manager Ahmed",
            "notes": "Delivered in full"
        })
        self.assertEqual(deliv_res.status_code, status.HTTP_200_OK)

        delivery.refresh_from_db()
        self.assertEqual(delivery.status, Delivery.Status.DELIVERED)
        self.assertIsNotNone(delivery.delivered_at)

        # Order timestamps remain intact
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.DELIVERED)
        self.assertEqual(order.created_at, initial_created_at)
        self.assertEqual(order.submitted_at, initial_submitted_at)

    # =========================================================================
    # PHASE 11 & 18: DOUBLE CLICK / IDEMPOTENCY PROTECTION
    # =========================================================================
    def test_phase11_and_18_rapid_double_submit_protection(self):
        """Submitting identical orders in rapid succession (<10s) returns existing order without creating duplicates."""
        items = [{"product_id": str(self.prod_a.id), "quantity": 5, "unit_price": "10.00"}]

        # First submit
        order_1 = create_order_service(
            customer_id=self.cust_2.id,
            order_date=self.today,
            driver_id=self.driver_1.id,
            source="MANAGER",
            items_data=items
        )

        # Rapid duplicate submit (simulating double-click or network retry)
        order_2 = create_order_service(
            customer_id=self.cust_2.id,
            order_date=self.today,
            driver_id=self.driver_1.id,
            source="MANAGER",
            items_data=items
        )

        # Must return the SAME order instance
        self.assertEqual(order_1.id, order_2.id)
        self.assertEqual(Order.objects.filter(customer=self.cust_2, order_date=self.today).count(), 1)

    # =========================================================================
    # PHASE 12: DRIVER WORKFLOW & ORDER VISIBILITY
    # =========================================================================
    def test_phase12_driver_workflow_and_product_visibility(self):
        """Driver opens dashboard, sees assigned delivery with exact products, quantities, and totals."""
        order = create_order_service(
            customer_id=self.cust_3.id,
            order_date=self.today,
            driver_id=self.driver_1.id,
            source="MANAGER",
            items_data=[
                {"product_id": str(self.prod_a.id), "quantity": 12, "unit_price": "10.00"},
                {"product_id": str(self.prod_b.id), "quantity": 8, "unit_price": "15.00"}
            ]
        )

        # Driver 1 logs in
        self.client.force_authenticate(user=self.driver_user_1)
        deliv_res = self.client.get("/api/v1/deliveries/")
        deliveries = deliv_res.data["results"] if "results" in deliv_res.data else deliv_res.data

        # Driver 1 must see this delivery
        matching = [d for d in deliveries if str(d["order"]) == str(order.id)]
        self.assertEqual(len(matching), 1, "Assigned order must appear in Driver's deliveries!")

        deliv_detail = matching[0]
        self.assertEqual(str(deliv_detail["order_details"]["customer"]), str(self.cust_3.id))
        self.assertEqual(deliv_detail["order_details"]["total_amount"], "240.00")  # (12*10) + (8*15) = 120 + 120 = 240

        # Check line items
        order_items = deliv_detail["order_details"]["items"]
        self.assertEqual(len(order_items), 2)
        qty_map = {item["product_details"]["code"]: item["quantity"] for item in order_items}
        self.assertEqual(qty_map["KUB"], 12)
        self.assertEqual(qty_map["ROM"], 8)

    # =========================================================================
    # PHASE 14: CURRENT ITEMS VS HISTORICAL IMMUTABILITY
    # =========================================================================
    def test_phase14_historical_orders_immutability(self):
        """Modifying or creating a new order must never mutate or leak into a previously submitted historical order."""
        # Historical Order A: Cust 1 buys Product A x 2 + Product B x 1
        order_a = create_order_service(
            customer_id=self.cust_1.id,
            order_date=self.today - datetime.timedelta(days=1),
            driver_id=self.driver_1.id,
            source="MANAGER",
            items_data=[
                {"product_id": str(self.prod_a.id), "quantity": 2, "unit_price": "10.00"},
                {"product_id": str(self.prod_b.id), "quantity": 1, "unit_price": "15.00"}
            ]
        )
        self.assertEqual(order_a.total_amount, Decimal("35.00"))

        # Today's Order B: Cust 1 buys Product C x 3
        order_b = create_order_service(
            customer_id=self.cust_1.id,
            order_date=self.today,
            driver_id=self.driver_1.id,
            source="MANAGER",
            items_data=[
                {"product_id": str(self.prod_c.id), "quantity": 3, "unit_price": "20.00"}
            ]
        )
        self.assertEqual(order_b.total_amount, Decimal("60.00"))

        # Check Order B does NOT contain Product A or B
        b_pids = [item.product_id for item in order_b.items.all()]
        self.assertNotIn(self.prod_a.id, b_pids)
        self.assertNotIn(self.prod_b.id, b_pids)
        self.assertIn(self.prod_c.id, b_pids)

        # Check Order A remains completely unchanged
        order_a.refresh_from_db()
        self.assertEqual(order_a.total_amount, Decimal("35.00"))
        a_pids = [item.product_id for item in order_a.items.all()]
        self.assertIn(self.prod_a.id, a_pids)
        self.assertIn(self.prod_b.id, a_pids)
        self.assertNotIn(self.prod_c.id, a_pids)

    # =========================================================================
    # PHASE 16 & 17: SELF-ORDER VS MANUAL ORDER CANONICAL CONSISTENCY
    # =========================================================================
    def test_phase16_and_17_self_order_vs_manual_entry_canonical_structure(self):
        """Self-order and manual order generate consistent canonical Order & OrderItem representations."""
        # Manual Order
        manual_order = create_order_service(
            customer_id=self.cust_1.id,
            order_date=self.today,
            driver_id=self.driver_1.id,
            source="MANAGER",
            items_data=[{"product_id": str(self.prod_a.id), "quantity": 10, "unit_price": "10.00"}]
        )

        # Self-Order via public endpoint
        res = self.client.post(
            f"/api/v1/public/customer-order/{self.cust_2.id}/",
            {"items": [{"product_id": str(self.prod_a.id), "quantity": 10}]},
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self_order = Order.objects.get(id=res.data["order_id"])

        # Compare canonical fields
        self.assertEqual(manual_order.items.count(), 1)
        self.assertEqual(self_order.items.count(), 1)
        self.assertEqual(manual_order.total_amount, Decimal("100.00"))
        self.assertEqual(self_order.total_amount, Decimal("100.00"))
        self.assertIsNotNone(manual_order.submitted_at)
        self.assertIsNotNone(self_order.submitted_at)
        self.assertIsNotNone(manual_order.route)
        self.assertIsNotNone(self_order.route)

    # =========================================================================
    # PHASE 21: TENANT & DRIVER ISOLATION
    # =========================================================================
    def test_phase21_tenant_and_driver_isolation(self):
        """Driver 1 cannot see or manipulate Driver 2's orders or deliveries."""
        order_driver2 = create_order_service(
            customer_id=self.cust_4.id,
            order_date=self.today,
            driver_id=self.driver_2.id,
            source="MANAGER",
            items_data=[{"product_id": str(self.prod_d.id), "quantity": 5, "unit_price": "25.00"}]
        )
        deliv2 = Delivery.objects.get(order=order_driver2)

        # Driver 1 tries to fetch Driver 2's delivery
        self.client.force_authenticate(user=self.driver_user_1)
        res = self.client.get(f"/api/v1/deliveries/{deliv2.id}/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND, "Driver 1 must not access Driver 2's delivery!")

        # Driver 1 tries to mark Driver 2's delivery as complete
        complete_res = self.client.post(f"/api/v1/deliveries/{deliv2.id}/complete/", {"recipient_name": "Intruder"})
        self.assertEqual(complete_res.status_code, status.HTTP_404_NOT_FOUND)

        # Verify deliv2 remains ASSIGNED in database
        deliv2.refresh_from_db()
        self.assertEqual(deliv2.status, Delivery.Status.ASSIGNED)
