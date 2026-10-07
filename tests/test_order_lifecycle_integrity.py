import datetime
from decimal import Decimal
import zoneinfo
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from apps.accounts.models import User
from apps.customers.models import Customer
from apps.products.models import Product
from apps.routes.models import Route, Driver
from apps.orders.models import Order
from apps.payments.models import Payment
from apps.credits.models import CreditTransaction
from apps.reports.models import DailyClosing
from apps.common.models import SystemSettings
from apps.orders.services import create_order_service, generate_order_number
from apps.customers.services import get_customers_opening_balances_for_date

class OrderLifecycleIntegrityTests(APITestCase):
    def setUp(self):
        # Settings
        self.settings = SystemSettings.get_settings()
        self.settings.is_self_order_enabled = True
        self.settings.is_maintenance_mode = False
        self.settings.save()

        # Manager user
        self.manager = User.objects.create_user(
            username="manager_test",
            email="manager@zamzam.test",
            password="ManagerPass123!",
            role=User.Role.MANAGER,
            first_name="Zayd",
        )
        self.driver_user = User.objects.create_user(
            username="driver_test",
            email="driver@zamzam.test",
            password="DriverPass123!",
            role=User.Role.DRIVER,
            first_name="Riyas",
        )
        self.driver_user_2 = User.objects.create_user(
            username="driver_test_2",
            email="driver2@zamzam.test",
            password="DriverPass123!",
            role=User.Role.DRIVER,
            first_name="Ali",
        )

        # Route & Drivers
        self.route_1 = Route.objects.create(name="Jeeto Route", code="JTO")
        self.route_2 = Route.objects.create(name="Town Route", code="TWN")
        self.driver_1 = Driver.objects.create(user=self.driver_user, assigned_route=self.route_1, is_active=True)
        self.driver_2 = Driver.objects.create(user=self.driver_user_2, assigned_route=self.route_2, is_active=True)

        # Customer Shop
        self.customer = Customer.objects.create(
            name="FAMOUS KATTANGAL",
            owner_name="riyas",
            phone="9800539574",
            address="Kattangal",
            route=self.route_1,
            current_balance=Decimal("5010.00"),
        )

        # Products
        self.kubbus = Product.objects.create(name="Kubbus", code="KBS", unit_price=Decimal("4.50"), is_active=True)
        self.romali = Product.objects.create(name="Romali", code="ROM", unit_price=Decimal("9.00"), is_active=True)

        # Pre-open business days so validation passes
        for d_str in ["2026-10-01", "2026-10-02", "2026-10-03"]:
            d_val = datetime.date.fromisoformat(d_str)
            DailyClosing.objects.get_or_create(date=d_val, defaults={"is_opened": True, "is_closed": False})

    def test_1_new_orders_have_distinct_ids(self):
        """Test 1: Creating Oct 1 and Oct 2 orders produces distinct unique IDs and numbers."""
        o1 = create_order_service(
            customer_id=self.customer.id,
            items_data=[{"product_id": self.kubbus.id, "quantity": 80, "unit_price": "4.50"}],
            order_date="2026-10-01",
            created_by=self.manager,
        )
        o2 = create_order_service(
            customer_id=self.customer.id,
            items_data=[{"product_id": self.kubbus.id, "quantity": 100, "unit_price": "4.50"}],
            order_date="2026-10-02",
            created_by=self.manager,
        )
        self.assertNotEqual(o1.id, o2.id)
        self.assertNotEqual(o1.order_number, o2.order_number)
        self.assertTrue(o1.order_number.startswith("ORD-20261001-"))
        self.assertTrue(o2.order_number.startswith("ORD-20261002-"))

    def test_2_order_number_consistent_with_business_date(self):
        """Test 2: Order for Oct 02 strictly receives ORD-20261002-XXXX, never ORD-20261003-."""
        o = create_order_service(
            customer_id=self.customer.id,
            items_data=[{"product_id": self.kubbus.id, "quantity": 100, "unit_price": "4.50"}],
            order_date="2026-10-02",
            order_number="ORD-20261003-0022",  # Sent mismatched date prefix
            created_by=self.manager,
        )
        self.assertEqual(o.order_date, datetime.date(2026, 10, 2))
        self.assertTrue(o.order_number.startswith("ORD-20261002-"))
        self.assertIn("0022", o.order_number)

    def test_3_new_order_does_not_inherit_previous_items_or_payment(self):
        """Test 3: Creating an order for Oct 3 starts with clean state and does not copy Oct 1 items/totals."""
        o1 = create_order_service(
            customer_id=self.customer.id,
            items_data=[
                {"product_id": self.kubbus.id, "quantity": 80, "unit_price": "4.50"},
                {"product_id": self.romali.id, "quantity": 10, "unit_price": "9.00"},
            ],
            order_date="2026-10-01",
            created_by=self.manager,
        )
        # 80 * 4.5 = 360, 10 * 9 = 90 -> total 450
        self.assertEqual(o1.total_amount, Decimal("450.00"))

        # Oct 3 new order with single item
        o3 = create_order_service(
            customer_id=self.customer.id,
            items_data=[{"product_id": self.romali.id, "quantity": 5, "unit_price": "9.00"}],
            order_date="2026-10-03",
            created_by=self.manager,
        )
        self.assertEqual(o3.total_amount, Decimal("45.00"))
        self.assertEqual(o3.items.count(), 1)
        self.assertEqual(o3.items.first().product, self.romali)

    def test_4_two_orders_same_customer_independent_totals(self):
        """Test 4: Two orders for the same customer have completely independent items and totals."""
        o1 = create_order_service(
            customer_id=self.customer.id,
            items_data=[{"product_id": self.kubbus.id, "quantity": 100, "unit_price": "4.50"}],
            order_date="2026-10-01",
            created_by=self.manager,
        )
        o2 = create_order_service(
            customer_id=self.customer.id,
            items_data=[
                {"product_id": self.kubbus.id, "quantity": 50, "unit_price": "4.50"},
                {"product_id": self.romali.id, "quantity": 10, "unit_price": "9.00"},
            ],
            order_date="2026-10-02",
            created_by=self.manager,
        )
        self.assertEqual(o1.total_amount, Decimal("450.00"))
        self.assertEqual(o2.total_amount, Decimal("315.00"))

    def test_5_self_order_submission_in_asia_kolkata_timezone(self):
        """Test 5: Self-order placed via public endpoint stamps order_date in Asia/Kolkata and creates independent order."""
        kolkata_tz = zoneinfo.ZoneInfo("Asia/Kolkata")
        expected_today = timezone.now().astimezone(kolkata_tz).date()

        res = self.client.post(
            f"/api/v1/public/customer-order/{self.customer.id}/",
            data={
                "items": [
                    {"product_id": str(self.kubbus.id), "quantity": 100},
                    {"product_id": str(self.romali.id), "quantity": 10},
                ]
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        order_num = res.data["order_number"]
        self.assertTrue(order_num.startswith(f"ORD-{expected_today.strftime('%Y%m%d')}-"))

        order_obj = Order.objects.get(order_number=order_num)
        self.assertEqual(order_obj.order_date, expected_today)
        self.assertEqual(order_obj.source, "CUSTOMER_LINK")
        self.assertEqual(order_obj.total_amount, Decimal("540.00"))

    def test_6_historical_opening_balances_roll_forward_continuously(self):
        """Test 6: Balances roll forward mathematically across days: Oct 1 closing becomes Oct 2 opening, Oct 2 closing becomes Oct 3 opening."""
        # Start: Customer balance = 5010.00
        # Oct 1: Order = 360.00, Payment = 500.00 -> Net -140 -> Balance becomes 4870.00
        o1 = create_order_service(
            customer_id=self.customer.id,
            items_data=[{"product_id": self.kubbus.id, "quantity": 80, "unit_price": "4.50"}],
            order_date="2026-10-01",
            created_by=self.manager,
        )
        p1 = Payment.objects.create(
            payment_number="PAY-20261001-0001",
            customer=self.customer,
            amount=Decimal("500.00"),
            payment_method=Payment.Method.CASH,
            status=Payment.Status.COMPLETED,
            collected_by=self.manager,
            received_at=timezone.make_aware(datetime.datetime(2026, 10, 1, 12, 0)),
        )

        # Oct 2: Order = 540.00, Payment = 0.00 -> Net +540 -> Balance becomes 5410.00
        o2 = create_order_service(
            customer_id=self.customer.id,
            items_data=[
                {"product_id": self.kubbus.id, "quantity": 100, "unit_price": "4.50"},
                {"product_id": self.romali.id, "quantity": 10, "unit_price": "9.00"},
            ],
            order_date="2026-10-02",
            created_by=self.manager,
        )

        # Recalculate customer's balance to current truth: 5010 + 360 - 500 + 540 = 5410
        self.customer.current_balance = Decimal("5410.00")
        self.customer.save()

        # Query balances for Oct 1, Oct 2, Oct 3
        b_oct1 = get_customers_opening_balances_for_date("2026-10-01", [self.customer.id])
        b_oct2 = get_customers_opening_balances_for_date("2026-10-02", [self.customer.id])
        b_oct3 = get_customers_opening_balances_for_date("2026-10-03", [self.customer.id])

        # Opening on Oct 1 MUST be 5010.00
        self.assertEqual(Decimal(b_oct1[str(self.customer.id)]), Decimal("5010.00"))
        # Opening on Oct 2 MUST be 5010 + 360 - 500 = 4870.00
        self.assertEqual(Decimal(b_oct2[str(self.customer.id)]), Decimal("4870.00"))
        # Opening on Oct 3 MUST be 4870 + 540 = 5410.00 (NOT jumping backwards to 4870!)
        self.assertEqual(Decimal(b_oct3[str(self.customer.id)]), Decimal("5410.00"))

    def test_7_double_submit_protection(self):
        """Test 7: Double submit within 5 seconds returns existing order instead of creating duplicate."""
        items = [{"product_id": self.kubbus.id, "quantity": 50, "unit_price": "4.50"}]
        o1 = create_order_service(
            customer_id=self.customer.id,
            items_data=items,
            order_date="2026-10-02",
            created_by=self.manager,
        )
        o2 = create_order_service(
            customer_id=self.customer.id,
            items_data=items,
            order_date="2026-10-02",
            created_by=self.manager,
        )
        self.assertEqual(o1.id, o2.id)
        self.assertEqual(Order.objects.filter(customer=self.customer, order_date="2026-10-02").count(), 1)

    def test_8_date_boundary_asia_kolkata(self):
        """Test 8: Date resolution explicitly respects Asia/Kolkata timezone."""
        order_num = generate_order_number(order_date=None)
        kolkata_tz = zoneinfo.ZoneInfo("Asia/Kolkata")
        expected_today = timezone.now().astimezone(kolkata_tz).date()
        self.assertTrue(order_num.startswith(f"ORD-{expected_today.strftime('%Y%m%d')}-"))

    def test_9_payments_do_not_bleed_across_orders(self):
        """Test 9: Payments recorded for one date/order do not bleed into other orders."""
        o1 = create_order_service(
            customer_id=self.customer.id,
            items_data=[{"product_id": self.kubbus.id, "quantity": 80, "unit_price": "4.50"}],
            order_date="2026-10-01",
            created_by=self.manager,
        )
        p1 = Payment.objects.create(
            payment_number="PAY-20261001-0001",
            customer=self.customer,
            order=o1,
            amount=Decimal("360.00"),
            payment_method=Payment.Method.CASH,
            status=Payment.Status.COMPLETED,
            collected_by=self.manager,
        )

        o2 = create_order_service(
            customer_id=self.customer.id,
            items_data=[{"product_id": self.kubbus.id, "quantity": 100, "unit_price": "4.50"}],
            order_date="2026-10-02",
            created_by=self.manager,
        )
        self.assertEqual(o1.payments.count(), 1)
        self.assertEqual(o2.payments.count(), 0)

    def test_10_driver_route_assignment_isolated_per_order(self):
        """Test 10: Two orders for same customer can retain independent driver assignments."""
        o1 = create_order_service(
            customer_id=self.customer.id,
            items_data=[{"product_id": self.kubbus.id, "quantity": 10, "unit_price": "4.50"}],
            order_date="2026-10-01",
            driver_id=self.driver_1.id,
            created_by=self.manager,
        )
        o2 = create_order_service(
            customer_id=self.customer.id,
            items_data=[{"product_id": self.kubbus.id, "quantity": 20, "unit_price": "4.50"}],
            order_date="2026-10-02",
            driver_id=self.driver_2.id,
            created_by=self.manager,
        )
        self.assertEqual(o1.driver, self.driver_1)
        self.assertEqual(o2.driver, self.driver_2)

    def test_11_prev_due_is_correct_after_two_orders(self):
        """
        Test 11 — Previous Due Correctness.
        Oct 1: Order ₹450, Payment ₹0 → outstanding ₹450
        Oct 2: Prev Due must be exactly ₹450
        """
        self.customer.current_balance = Decimal("0.00")
        self.customer.save()

        o1 = create_order_service(
            customer_id=self.customer.id,
            items_data=[{"product_id": self.kubbus.id, "quantity": 100, "unit_price": "4.50"}],
            order_date="2026-10-01",
            created_by=self.manager,
        )  # total = 450.00

        o2 = create_order_service(
            customer_id=self.customer.id,
            items_data=[{"product_id": self.kubbus.id, "quantity": 200, "unit_price": "4.50"}],
            order_date="2026-10-02",
            created_by=self.manager,
        )  # total = 900.00

        # Prev Due for Oct 2 must equal Oct 1 total (450.00)
        b_oct2 = get_customers_opening_balances_for_date("2026-10-02", [self.customer.id])
        self.assertEqual(
            Decimal(b_oct2[str(self.customer.id)]), Decimal("450.00"),
            "Prev Due for Oct 2 must equal Oct 1 outstanding"
        )

    def test_12_editing_oct2_does_not_change_oct1_total(self):
        """
        Test 12 — Edit Current Order Isolation.
        Edit Oct 2 by adding 1 unit. Oct 1 must remain completely unchanged.
        """
        from apps.orders.services import update_order_service

        self.customer.current_balance = Decimal("0.00")
        self.customer.save()

        o1 = create_order_service(
            customer_id=self.customer.id,
            items_data=[{"product_id": self.kubbus.id, "quantity": 100, "unit_price": "4.50"}],
            order_date="2026-10-01",
            created_by=self.manager,
        )
        oct1_total = o1.total_amount  # 450.00

        o2 = create_order_service(
            customer_id=self.customer.id,
            items_data=[{"product_id": self.kubbus.id, "quantity": 200, "unit_price": "4.50"}],
            order_date="2026-10-02",
            created_by=self.manager,
        )

        # Edit Oct 2: add 1 unit (+4.50)
        update_order_service(
            order_id=o2.id,
            items_data=[{"product_id": self.kubbus.id, "quantity": 201, "unit_price": "4.50"}],
            user=self.manager,
        )

        # Oct 1 total MUST be unchanged
        o1.refresh_from_db()
        self.assertEqual(o1.total_amount, oct1_total, "Oct 1 total must not change when Oct 2 is edited")

        # Oct 2 must be updated
        o2.refresh_from_db()
        self.assertEqual(o2.total_amount, Decimal("904.50"), "Oct 2 total must reflect edit")

    def test_13_edit_product_rate_only_affects_current_order(self):
        """
        Test 13 — Product Rate Change Isolation.
        Change one Oct 2 product rate by ₹1. Oct 1 must be completely unchanged.
        """
        from apps.orders.services import update_order_service

        self.customer.current_balance = Decimal("0.00")
        self.customer.save()

        o1 = create_order_service(
            customer_id=self.customer.id,
            items_data=[{"product_id": self.kubbus.id, "quantity": 100, "unit_price": "4.50"}],
            order_date="2026-10-01",
            created_by=self.manager,
        )
        o1_original_items = list(o1.items.values("product_id", "quantity", "unit_price"))
        o1_original_total = o1.total_amount  # 450.00

        o2 = create_order_service(
            customer_id=self.customer.id,
            items_data=[{"product_id": self.kubbus.id, "quantity": 100, "unit_price": "4.50"}],
            order_date="2026-10-02",
            created_by=self.manager,
        )

        # Edit Oct 2 with +₹1 unit price
        update_order_service(
            order_id=o2.id,
            items_data=[{"product_id": self.kubbus.id, "quantity": 100, "unit_price": "4.51"}],
            user=self.manager,
        )

        # Oct 1 items and total must be unchanged
        o1.refresh_from_db()
        current_o1_items = list(o1.items.values("product_id", "quantity", "unit_price"))
        self.assertEqual(o1_original_items, current_o1_items, "Oct 1 items must not change after Oct 2 rate edit")
        self.assertEqual(o1.total_amount, o1_original_total, "Oct 1 total must not change after Oct 2 rate edit")

        # Oct 2 must be updated
        o2.refresh_from_db()
        self.assertEqual(o2.total_amount, Decimal("451.00"), "Oct 2 total must reflect +₹1 rate change")

    def test_14_prev_due_stable_after_multiple_edits(self):
        """
        Test 14 — Previous Due Stability After Multiple Edits.
        Edit Oct 2 five times. Prev Due for Oct 2 must remain identical after every edit.
        """
        from apps.orders.services import update_order_service

        self.customer.current_balance = Decimal("0.00")
        self.customer.save()

        o1 = create_order_service(
            customer_id=self.customer.id,
            items_data=[{"product_id": self.kubbus.id, "quantity": 100, "unit_price": "4.50"}],
            order_date="2026-10-01",
            created_by=self.manager,
        )  # 450.00

        o2 = create_order_service(
            customer_id=self.customer.id,
            items_data=[{"product_id": self.kubbus.id, "quantity": 100, "unit_price": "4.50"}],
            order_date="2026-10-02",
            created_by=self.manager,
        )

        prev_due_initial = Decimal(
            get_customers_opening_balances_for_date("2026-10-02", [self.customer.id])[str(self.customer.id)]
        )
        self.assertEqual(prev_due_initial, Decimal("450.00"), "Initial Prev Due for Oct 2 must equal Oct 1 total")

        # Edit Oct 2 five times with incrementing quantities
        for qty in [101, 102, 103, 104, 105]:
            update_order_service(
                order_id=o2.id,
                items_data=[{"product_id": self.kubbus.id, "quantity": qty, "unit_price": "4.50"}],
                user=self.manager,
            )
            prev_due_after = Decimal(
                get_customers_opening_balances_for_date("2026-10-02", [self.customer.id])[str(self.customer.id)]
            )
            self.assertEqual(
                prev_due_after, Decimal("450.00"),
                f"Prev Due for Oct 2 must remain ₹450 after editing Oct 2 (qty={qty}), got ₹{prev_due_after}"
            )

    def test_15_payment_change_does_not_affect_oct1(self):
        """
        Test 15 — Payment Independence.
        Change Oct 2 payment. Oct 1 total and payment records must remain unchanged.
        """
        self.customer.current_balance = Decimal("0.00")
        self.customer.save()

        o1 = create_order_service(
            customer_id=self.customer.id,
            items_data=[{"product_id": self.kubbus.id, "quantity": 100, "unit_price": "4.50"}],
            order_date="2026-10-01",
            created_by=self.manager,
        )

        o2 = create_order_service(
            customer_id=self.customer.id,
            items_data=[{"product_id": self.kubbus.id, "quantity": 100, "unit_price": "4.50"}],
            order_date="2026-10-02",
            created_by=self.manager,
        )

        # Add a payment for Oct 2
        p2 = Payment.objects.create(
            payment_number="PAY-20261002-TEST",
            customer=self.customer,
            order=o2,
            amount=Decimal("200.00"),
            payment_method=Payment.Method.CASH,
            status=Payment.Status.COMPLETED,
            collected_by=self.manager,
        )

        self.assertEqual(o1.payments.count(), 0, "Oct 1 should have zero payments")
        self.assertEqual(o2.payments.count(), 1, "Oct 2 should have one payment")

        # Edit payment amount for Oct 2
        p2.amount = Decimal("540.00")
        p2.save()

        o1.refresh_from_db()
        self.assertEqual(o1.payments.count(), 0, "Oct 1 payments must not change")
        self.assertEqual(o1.total_amount, Decimal("450.00"), "Oct 1 total must not change")

    def test_16_three_order_independence(self):
        """
        Test 16 — Three Orders Independence.
        Create Oct 1, Oct 2, Oct 3. Edit Oct 2. Verify Oct 1 and Oct 3 are untouched.
        """
        from apps.orders.services import update_order_service

        self.customer.current_balance = Decimal("0.00")
        self.customer.save()

        o1 = create_order_service(
            customer_id=self.customer.id,
            items_data=[{"product_id": self.kubbus.id, "quantity": 100, "unit_price": "4.50"}],
            order_date="2026-10-01",
            created_by=self.manager,
        )  # 450.00

        o2 = create_order_service(
            customer_id=self.customer.id,
            items_data=[{"product_id": self.kubbus.id, "quantity": 200, "unit_price": "4.50"}],
            order_date="2026-10-02",
            created_by=self.manager,
        )  # 900.00

        o3 = create_order_service(
            customer_id=self.customer.id,
            items_data=[{"product_id": self.kubbus.id, "quantity": 300, "unit_price": "4.50"}],
            order_date="2026-10-03",
            created_by=self.manager,
        )  # 1350.00

        oct1_total = o1.total_amount
        oct3_total = o3.total_amount

        # Edit Oct 2: change 1 unit
        update_order_service(
            order_id=o2.id,
            items_data=[{"product_id": self.kubbus.id, "quantity": 201, "unit_price": "4.50"}],
            user=self.manager,
        )  # 904.50

        # Oct 1 and Oct 3 must be completely unchanged
        o1.refresh_from_db()
        o3.refresh_from_db()
        self.assertEqual(o1.total_amount, oct1_total, "Oct 1 total must not change after Oct 2 edit")
        self.assertEqual(o3.total_amount, oct3_total, "Oct 3 total must not change after Oct 2 edit")

        # Prev Due for Oct 2 = Oct 1 total (unchanged)
        b_oct2 = get_customers_opening_balances_for_date("2026-10-02", [self.customer.id])
        self.assertEqual(Decimal(b_oct2[str(self.customer.id)]), oct1_total)

    def test_17_credit_sale_updated_in_place_no_adjustment_transactions(self):
        """
        Test 17 — Credit Sale In-Place Update.
        When an order is edited, the CREDIT_SALE ledger entry must be updated in-place.
        No new ADJUSTMENT transaction with reference_order should be created.
        This prevents ghost transactions from distorting Prev. Due for any date.
        """
        from apps.orders.services import update_order_service
        from apps.credits.models import CreditTransaction

        self.customer.current_balance = Decimal("0.00")
        self.customer.save()

        o1 = create_order_service(
            customer_id=self.customer.id,
            items_data=[{"product_id": self.kubbus.id, "quantity": 100, "unit_price": "4.50"}],
            order_date="2026-10-01",
            created_by=self.manager,
        )  # 450.00

        # Verify initial CREDIT_SALE entry
        initial_sale_tx = CreditTransaction.objects.filter(
            reference_order=o1,
            transaction_type=CreditTransaction.TransactionType.CREDIT_SALE,
        ).first()
        self.assertIsNotNone(initial_sale_tx, "CREDIT_SALE entry must exist after order creation")
        self.assertEqual(initial_sale_tx.amount, Decimal("450.00"))

        # Edit Oct 1 order (+1 unit = +4.50)
        update_order_service(
            order_id=o1.id,
            items_data=[{"product_id": self.kubbus.id, "quantity": 101, "unit_price": "4.50"}],
            user=self.manager,
        )  # new total = 454.50

        # CREDIT_SALE must be updated in-place — still exactly ONE entry
        sale_txs = CreditTransaction.objects.filter(
            reference_order=o1,
            transaction_type=CreditTransaction.TransactionType.CREDIT_SALE,
        )
        self.assertEqual(sale_txs.count(), 1, "Only one CREDIT_SALE entry should exist per order after edit")
        updated_sale_tx = sale_txs.first()
        self.assertEqual(updated_sale_tx.amount, Decimal("454.50"), "CREDIT_SALE amount must reflect new order total")

        # No ADJUSTMENT transaction linked to this order should exist
        adj_txs = CreditTransaction.objects.filter(
            reference_order=o1,
            transaction_type=CreditTransaction.TransactionType.ADJUSTMENT,
        )
        self.assertEqual(adj_txs.count(), 0, "No ADJUSTMENT transactions should be created for order edits")
