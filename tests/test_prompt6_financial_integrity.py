from decimal import Decimal
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from django.db import transaction

from apps.accounts.models import User
from apps.customers.models import Customer
from apps.routes.models import Route, Driver, DriverExpense
from apps.products.models import Product
from apps.orders.models import Order, OrderItem
from apps.deliveries.models import Delivery
from apps.deliveries.services import complete_delivery_service
from apps.payments.models import Payment
from apps.payments.services import record_payment_service, reverse_payment_service
from apps.credits.models import CreditTransaction
from apps.credits.services import record_opening_balance_service, record_adjustment_service


class FinancialIntegrityPrompt6Tests(APITestCase):
    """
    Comprehensive test suite for Prompt 6:
    - Decimal precision & financial correctness
    - Customer Credit Ledger & transaction history
    - Payment allocation (Order vs Previous Credit)
    - Reversal / Void safeguards (no silent deletes)
    - Collection reports & Aging outstanding reports
    - Driver operational collections & net cashflow
    - Atomic rollback on transaction failures
    """

    def setUp(self):
        # 1. Users
        self.owner = User.objects.create_user(
            username="owner_fin",
            email="owner_fin@example.com",
            password="password123",
            role=User.Role.OWNER,
        )
        self.manager = User.objects.create_user(
            username="mgr_fin",
            email="mgr_fin@example.com",
            password="password123",
            role=User.Role.MANAGER,
        )
        self.driver_user = User.objects.create_user(
            username="driver_fin",
            email="driver_fin@example.com",
            password="password123",
            role=User.Role.DRIVER,
        )

        # 2. Route & Driver
        self.route = Route.objects.create(name="Financial Route", code="FIN-01")
        self.driver = Driver.objects.create(
            user=self.driver_user,
            assigned_route=self.route,
            phone_number="9876543210",
            vehicle_number="KL-10-FIN-1234",
            license_number="LIC-FIN-01",
        )

        # 3. Product
        self.kubbus = Product.objects.create(
            name="Kubbus Pack",
            code="KUB-FIN",
            unit_price=Decimal("25.00"),
            packet_size="10 pieces",
        )

        # 4. Customer
        self.customer = Customer.objects.create(
            name="Al-Noor Bakery Shop",
            owner_name="Ahmed Noor",
            phone="9847000001",
            address="Market Road, Shop 10",
            route=self.route,
            credit_limit=Decimal("10000.00"),
            current_balance=Decimal("0.00"),
        )

    def test_prompt6_example_credit_flow_and_decimal_accuracy(self):
        """
        Validates Prompt 6 specific example:
        - Customer previous credit: ₹3,000.00
        - Today's order: ₹1,200.00
        - Payment: ₹500.00
        - Remaining outstanding: ₹3,700.00
        - Auditable balance_before, delta, and balance_after on ledger
        """
        # Step 1: Set opening credit of ₹3,000.00
        op_tx = record_opening_balance_service(
            customer=self.customer,
            opening_balance=Decimal("3000.00"),
            recorded_by=self.owner,
        )
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.current_balance, Decimal("3000.00"))
        self.assertEqual(op_tx.balance_after, Decimal("3000.00"))
        self.assertEqual(op_tx.balance_before, Decimal("0.00"))

        # Step 2: Today's order of ₹1,200.00 delivered
        order = Order.objects.create(
            order_number="ORD-FIN-1200",
            customer=self.customer,
            route=self.route,
            driver=self.driver,
            order_date=timezone.now().date(),
            total_amount=Decimal("1200.00"),
            status=Order.Status.CONFIRMED,
        )
        delivery = Delivery.objects.create(
            order=order,
            route=self.route,
            driver=self.driver,
            status=Delivery.Status.ASSIGNED,
        )
        complete_delivery_service(delivery_id=delivery.id, recipient_name="Ahmed", user=self.driver_user)

        self.customer.refresh_from_db()
        self.assertEqual(self.customer.current_balance, Decimal("4200.00"))  # 3000 + 1200

        sale_tx = CreditTransaction.objects.filter(reference_order=order).first()
        self.assertIsNotNone(sale_tx)
        self.assertEqual(sale_tx.amount, Decimal("1200.00"))
        self.assertEqual(sale_tx.balance_before, Decimal("3000.00"))
        self.assertEqual(sale_tx.balance_after, Decimal("4200.00"))

        # Step 3: Payment of ₹500.00
        pay = record_payment_service(
            customer_id=self.customer.id,
            amount=Decimal("500.00"),
            payment_method=Payment.Method.CASH,
            collected_by=self.driver_user,
            order_id=None,  # payment against credit
            reference_number="REC-500",
            notes="Cash payment against credit debt",
        )

        self.customer.refresh_from_db()
        # Remaining outstanding = 4200 - 500 = 3700
        self.assertEqual(self.customer.current_balance, Decimal("3700.00"))

        pay_tx = CreditTransaction.objects.filter(reference_payment=pay).first()
        self.assertIsNotNone(pay_tx)
        self.assertEqual(pay_tx.amount, Decimal("-500.00"))
        self.assertEqual(pay_tx.balance_before, Decimal("4200.00"))
        self.assertEqual(pay_tx.balance_after, Decimal("3700.00"))

    def test_payment_allocation_explicit_separation(self):
        """
        When payment is recorded against previous credit:
        do not incorrectly mark today's order as paid.
        Payment allocation must be explicit.
        """
        # Create order for today
        order = Order.objects.create(
            order_number="ORD-FIN-ALLOC-01",
            customer=self.customer,
            route=self.route,
            driver=self.driver,
            order_date=timezone.now().date(),
            total_amount=Decimal("1500.00"),
            status=Order.Status.CONFIRMED,
        )

        # Payment recorded explicitly for previous credit (order_id is None)
        self.client.force_authenticate(user=self.driver_user)
        response = self.client.post(
            "/api/v1/payments/",
            {
                "customer_id": str(self.customer.id),
                "payment_type": "PREVIOUS_CREDIT",
                "amount": "600.00",
                "payment_method": "CASH",
                "notes": "Paid towards previous credit balance",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data["payment_type"], "PREVIOUS_CREDIT")
        self.assertIsNone(data["order"])

        # Order remains unaffected
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CONFIRMED)
        self.assertEqual(order.payments.count(), 0)

    def test_payment_reversal_safeguard_and_balance_restoration(self):
        """
        Ensures payments can be reversed with a documented reason,
        restoring the customer's debt balance and posting to the credit ledger.
        """
        self.customer.current_balance = Decimal("2000.00")
        self.customer.save()

        # 1. Record payment of ₹800.00
        pay = record_payment_service(
            customer_id=self.customer.id,
            amount=Decimal("800.00"),
            payment_method=Payment.Method.GPAY_UPI,
            collected_by=self.driver_user,
            reference_number="UPI-REV-001",
        )
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.current_balance, Decimal("1200.00"))  # 2000 - 800

        # 2. Reverse payment by Manager
        self.client.force_authenticate(user=self.manager)
        rev_res = self.client.post(
            f"/api/v1/payments/{pay.id}/reverse/",
            {"reason": "Customer UPI transaction bounced at bank"},
            format="json",
        )
        self.assertEqual(rev_res.status_code, status.HTTP_200_OK)
        rev_data = rev_res.json()
        self.assertEqual(rev_data["status"], "REVERSED")
        self.assertEqual(rev_data["reversal_reason"], "Customer UPI transaction bounced at bank")

        # 3. Check customer balance restored
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.current_balance, Decimal("2000.00"))

        # 4. Check credit transaction on ledger
        rev_tx = CreditTransaction.objects.filter(
            reference_payment=pay,
            transaction_type=CreditTransaction.TransactionType.PAYMENT_REVERSAL,
        ).first()
        self.assertIsNotNone(rev_tx)
        self.assertEqual(rev_tx.amount, Decimal("800.00"))  # positive delta restores debt
        self.assertEqual(rev_tx.balance_after, Decimal("2000.00"))

        # 5. Cannot reverse an already reversed payment
        second_rev = self.client.post(
            f"/api/v1/payments/{pay.id}/reverse/",
            {"reason": "Trying again"},
            format="json",
        )
        self.assertEqual(second_rev.status_code, status.HTTP_400_BAD_REQUEST)

    def test_direct_deletion_prohibited_for_financial_records(self):
        """
        Users cannot silently delete or mutate financial payment records.
        """
        pay = record_payment_service(
            customer_id=self.customer.id,
            amount=Decimal("400.00"),
            payment_method=Payment.Method.CASH,
            collected_by=self.driver_user,
        )

        self.client.force_authenticate(user=self.owner)
        del_res = self.client.delete(f"/api/v1/payments/{pay.id}/")
        self.assertEqual(del_res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        put_res = self.client.put(f"/api/v1/payments/{pay.id}/", {"amount": "100.00"})
        self.assertEqual(put_res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_collections_report_endpoint(self):
        """
        Tests /api/v1/reports/collections/ with Cash, UPI, and previous credit breakdowns.
        """
        # Payment 1: Cash
        record_payment_service(
            customer_id=self.customer.id,
            amount=Decimal("300.00"),
            payment_method=Payment.Method.CASH,
            collected_by=self.driver_user,
        )
        # Payment 2: UPI
        record_payment_service(
            customer_id=self.customer.id,
            amount=Decimal("700.00"),
            payment_method=Payment.Method.GPAY_UPI,
            collected_by=self.driver_user,
        )

        self.client.force_authenticate(user=self.owner)
        res = self.client.get("/api/v1/reports/collections/?date_preset=today")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()

        self.assertEqual(Decimal(data["summary"]["total_collected"]), Decimal("1000.00"))
        self.assertEqual(Decimal(data["summary"]["cash_total"]), Decimal("300.00"))
        self.assertEqual(Decimal(data["summary"]["upi_total"]), Decimal("700.00"))
        self.assertEqual(len(data["collections"]), 2)

    def test_outstanding_customers_report_aging(self):
        """
        Tests /api/v1/reports/outstanding-credit/ showing debt aging and last payment/order.
        """
        self.customer.current_balance = Decimal("2500.00")
        self.customer.save()

        # Record payment yesterday
        yesterday = timezone.now() - timezone.timedelta(days=1)
        record_payment_service(
            customer_id=self.customer.id,
            amount=Decimal("500.00"),
            payment_method=Payment.Method.CASH,
            collected_by=self.driver_user,
            received_at=yesterday,
        )

        self.client.force_authenticate(user=self.manager)
        res = self.client.get("/api/v1/reports/outstanding-credit/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()

        self.assertGreaterEqual(len(data["customers"]), 1)
        cust_row = next((c for c in data["customers"] if c["customer_id"] == str(self.customer.id)), None)
        self.assertIsNotNone(cust_row)
        self.assertEqual(cust_row["aging_bucket"], "0-7 days")
        self.assertIsNotNone(cust_row["last_payment"])
        self.assertEqual(cust_row["last_payment"]["amount"], "500.00")

    def test_driver_collections_operational_report(self):
        """
        Tests operational driver collections report showing collections, expenses, and net collection.
        """
        # Driver collected 1000
        record_payment_service(
            customer_id=self.customer.id,
            amount=Decimal("1000.00"),
            payment_method=Payment.Method.CASH,
            collected_by=self.driver_user,
        )
        # Driver had 250 in petrol expense
        DriverExpense.objects.create(
            driver=self.driver,
            category=DriverExpense.Category.PETROL,
            amount=Decimal("250.00"),
            date=timezone.now().date(),
        )

        self.client.force_authenticate(user=self.owner)
        res = self.client.get("/api/v1/reports/driver-collections/?date_preset=today")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()

        d_row = next((d for d in data["drivers"] if d["driver_id"] == str(self.driver.id)), None)
        self.assertIsNotNone(d_row)
        self.assertEqual(Decimal(d_row["total_collected"]), Decimal("1000.00"))
        self.assertEqual(Decimal(d_row["expenses"]), Decimal("250.00"))
        self.assertEqual(Decimal(d_row["net_collection"]), Decimal("750.00"))

    def test_daily_financial_summary_endpoint(self):
        """
        Tests /api/v1/reports/financial-summary/ based on verified DB calculations.
        """
        order = Order.objects.create(
            order_number="ORD-FIN-SUM-01",
            customer=self.customer,
            route=self.route,
            driver=self.driver,
            order_date=timezone.now().date(),
            total_amount=Decimal("2000.00"),
            status=Order.Status.CONFIRMED,
        )
        record_payment_service(
            customer_id=self.customer.id,
            amount=Decimal("1200.00"),
            payment_method=Payment.Method.CASH,
            collected_by=self.driver_user,
            order_id=order.id,
        )
        DriverExpense.objects.create(
            driver=self.driver,
            category=DriverExpense.Category.FOOD,
            amount=Decimal("150.00"),
            date=timezone.now().date(),
        )

        self.client.force_authenticate(user=self.owner)
        res = self.client.get("/api/v1/reports/financial-summary/?date_preset=today")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()

        self.assertEqual(Decimal(data["sales"]), Decimal("2000.00"))
        self.assertEqual(Decimal(data["total_collected"]), Decimal("1200.00"))
        self.assertEqual(Decimal(data["today_order_collected"]), Decimal("1200.00"))
        self.assertEqual(Decimal(data["driver_expenses"]), Decimal("150.00"))
        self.assertEqual(Decimal(data["net_collection"]), Decimal("1050.00"))

    def test_atomic_transaction_rollback_on_failure(self):
        """
        Validates that if an error occurs mid-transaction, no partial records
        are created and the customer balance remains completely untouched.
        """
        initial_balance = Decimal("1500.00")
        self.customer.current_balance = initial_balance
        self.customer.save()

        initial_payment_count = Payment.objects.count()
        initial_credit_count = CreditTransaction.objects.count()

        # Attempt to record payment with invalid/negative amount
        with self.assertRaises(ValueError):
            record_payment_service(
                customer_id=self.customer.id,
                amount=Decimal("-200.00"),
                payment_method=Payment.Method.CASH,
                collected_by=self.driver_user,
            )

        # Database state must remain completely unaltered
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.current_balance, initial_balance)
        self.assertEqual(Payment.objects.count(), initial_payment_count)
        self.assertEqual(CreditTransaction.objects.count(), initial_credit_count)

    def test_decimal_precision_no_floating_point_drift(self):
        """
        Executes repeated micro-cents transactions to verify Decimal arithmetic
        never causes IEEE floating-point drift.
        """
        balance = Decimal("0.00")
        self.customer.current_balance = balance
        self.customer.save()

        # Add 3 items of ₹33.33 each
        for i in range(3):
            tx = record_adjustment_service(
                customer_id=self.customer.id,
                amount=Decimal("33.33"),
                notes=f"Fractional micro charge {i+1}",
                recorded_by=self.owner,
            )

        self.customer.refresh_from_db()
        # Exactly 99.99, not 99.99000000000001
        self.assertEqual(self.customer.current_balance, Decimal("99.99"))

        # Pay ₹99.99
        record_payment_service(
            customer_id=self.customer.id,
            amount=Decimal("99.99"),
            payment_method=Payment.Method.CASH,
            collected_by=self.driver_user,
        )

        self.customer.refresh_from_db()
        self.assertEqual(self.customer.current_balance, Decimal("0.00"))
