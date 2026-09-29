from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from apps.accounts.models import User
from apps.routes.models import Route, Driver
from apps.customers.models import Customer
from apps.products.models import Product
from apps.orders.services import create_order_service
from apps.deliveries.services import complete_delivery_service
from apps.payments.services import record_payment_service
from apps.payments.models import Payment
from apps.credits.models import CreditTransaction
from apps.credits.services import record_opening_balance_service

class PaymentAndCreditLedgerTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner", password="password", role=User.Role.OWNER
        )
        self.driver_user = User.objects.create_user(
            username="driver", password="password", role=User.Role.DRIVER
        )
        self.route = Route.objects.create(name="Pandikkad", code="PKD")
        self.driver = Driver.objects.create(
            user=self.driver_user,
            assigned_route=self.route,
            phone_number="9847111111"
        )
        self.shop = Customer.objects.create(
            name="ABC Bakery",
            phone="9847100000",
            address="Pandikkad",
            route=self.route,
            credit_limit=Decimal("10000.00")
        )
        self.product = Product.objects.create(
            name="Kubbus",
            code="KUB",
            unit_price=Decimal("35.00")
        )

    def test_complete_credit_ledger_lifecycle(self):
        """
        Tests the exact business lifecycle required:
        Opening balance +3000
        Credit sale (order delivery) +1400 (40 * 35.00)
        Cash payment -500
        GPay payment -300
        Current balance: 3600
        Verify all transactions exist in ledger with proper snapshot balances!
        """
        # 1. Opening Balance +3000.00
        record_opening_balance_service(
            customer=self.shop,
            opening_balance=Decimal("3000.00"),
            recorded_by=self.owner
        )
        self.shop.refresh_from_db()
        self.assertEqual(self.shop.current_balance, Decimal("3000.00"))

        # 2. Order for 40 Kubbus = 1400.00
        order = create_order_service(
            customer_id=self.shop.id,
            items_data=[{"product_id": self.product.id, "quantity": 40}],
            driver_id=self.driver.id,
            created_by=self.owner,
        )
        self.assertEqual(order.total_amount, Decimal("1400.00"))

        # Complete delivery -> triggers credit sale
        complete_delivery_service(
            delivery_id=order.delivery.id,
            recipient_name="Shop Keeper",
            user=self.driver_user
        )

        self.shop.refresh_from_db()
        # 3000 + 1400 = 4400.00
        self.assertEqual(self.shop.current_balance, Decimal("4400.00"))

        # 3. Cash Payment -500.00
        pay_cash = record_payment_service(
            customer_id=self.shop.id,
            amount=Decimal("500.00"),
            payment_method=Payment.Method.CASH,
            collected_by=self.driver_user,
            order_id=order.id
        )
        self.shop.refresh_from_db()
        # 4400 - 500 = 3900.00
        self.assertEqual(self.shop.current_balance, Decimal("3900.00"))

        # 4. GPay Payment -300.00
        pay_gpay = record_payment_service(
            customer_id=self.shop.id,
            amount=Decimal("300.00"),
            payment_method=Payment.Method.GPAY_UPI,
            collected_by=self.driver_user,
            order_id=order.id,
            reference_number="UPI-REF-998877"
        )
        self.shop.refresh_from_db()
        # 3900 - 300 = 3600.00
        self.assertEqual(self.shop.current_balance, Decimal("3600.00"))

        # Verify Credit Ledger Entries
        entries = CreditTransaction.objects.filter(customer=self.shop).order_by("created_at")
        self.assertEqual(entries.count(), 4)

        # Check entry types and snapshot balance_after values
        e1, e2, e3, e4 = list(entries)
        self.assertEqual(e1.transaction_type, CreditTransaction.TransactionType.OPENING_BALANCE)
        self.assertEqual(e1.balance_after, Decimal("3000.00"))

        self.assertEqual(e2.transaction_type, CreditTransaction.TransactionType.CREDIT_SALE)
        self.assertEqual(e2.balance_after, Decimal("4400.00"))

        self.assertEqual(e3.transaction_type, CreditTransaction.TransactionType.CASH_PAYMENT)
        self.assertEqual(e3.balance_after, Decimal("3900.00"))

        self.assertEqual(e4.transaction_type, CreditTransaction.TransactionType.GPAY_PAYMENT)
        self.assertEqual(e4.balance_after, Decimal("3600.00"))

    def test_payment_endpoint_via_api(self):
        self.client.force_authenticate(user=self.driver_user)
        url = reverse("api_v1:payment-list")
        res = self.client.post(url, {
            "customer_id": str(self.shop.id),
            "amount": "250.00",
            "payment_method": "CASH",
            "notes": "Collected cash",
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Decimal(res.data["amount"]), Decimal("250.00"))
