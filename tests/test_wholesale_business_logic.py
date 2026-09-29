import decimal
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User
from apps.customers.models import Customer, CustomerProductPrice
from apps.customers.services import get_effective_product_price, set_customer_product_price
from apps.products.models import Product
from apps.routes.models import Route, Driver, DriverExpense
from apps.orders.models import Order, OrderItem
from apps.orders.services import create_order_service
from apps.deliveries.models import Delivery
from apps.payments.models import Payment
from apps.credits.models import CreditTransaction


class WholesaleBusinessLogicTestCase(TestCase):
    """
    Automated test suite verifying the 20 business cases mandated in Prompt 2, Section 33.
    """

    def setUp(self):
        self.client = APIClient()

        # Users
        self.owner = User.objects.create_user(
            username='owner_user',
            email='owner@zamzam.com',
            password='password123',
            role=User.Role.OWNER,
        )
        self.manager = User.objects.create_user(
            username='manager_user',
            email='manager@zamzam.com',
            password='password123',
            role=User.Role.MANAGER,
        )
        self.driver_a_user = User.objects.create_user(
            username='driver_a_user',
            email='driver_a@zamzam.com',
            password='password123',
            role=User.Role.DRIVER,
        )
        self.driver_b_user = User.objects.create_user(
            username='driver_b_user',
            email='driver_b@zamzam.com',
            password='password123',
            role=User.Role.DRIVER,
        )

        # Routes
        self.route_pkd = Route.objects.create(name='Pandikkad', code='PKD')
        self.route_prd = Route.objects.create(name='Perundurai', code='PRD')

        # Drivers
        self.driver_a = Driver.objects.create(
            user=self.driver_a_user,
            assigned_route=self.route_pkd,
            phone_number='9847000001',
            vehicle_number='KL-10-AB-1234',
            license_number='DL-PKD-001',
        )
        self.driver_b = Driver.objects.create(
            user=self.driver_b_user,
            assigned_route=self.route_prd,
            phone_number='9847000002',
            vehicle_number='KL-10-CD-5678',
            license_number='DL-PRD-002',
        )

        # Products (Kubbus default base price = ₹12.00, Romali default = ₹15.00)
        self.product_kubbus = Product.objects.create(
            name='Kubbus',
            code='KUB-01',
            unit_price=Decimal('12.00'),
            packet_size='Pack of 10',
        )
        self.product_romali = Product.objects.create(
            name='Romali',
            code='ROM-01',
            unit_price=Decimal('15.00'),
            packet_size='Pack of 5',
        )

        # Customers
        self.customer_a = Customer.objects.create(
            name='Shop A Bakery',
            owner_name='Ahmad',
            phone='9847111111',
            address='Pandikkad Junction',
            route=self.route_pkd,
            credit_limit=Decimal('5000.00'),
            current_balance=Decimal('0.00'),
        )
        self.customer_b = Customer.objects.create(
            name='Shop B Tea Stall',
            owner_name='Basheer',
            phone='9847222222',
            address='Perundurai Bazaar',
            route=self.route_prd,
            credit_limit=Decimal('6000.00'),
            current_balance=Decimal('0.00'),
        )

    # 1. Customer A has Kubbus price ₹10.
    def test_case_01_customer_a_price_configuration(self):
        set_customer_product_price(self.customer_a, self.product_kubbus, Decimal('10.00'))
        eff_price, is_custom, _ = get_effective_product_price(self.customer_a, self.product_kubbus)
        self.assertEqual(eff_price, Decimal('10.00'))
        self.assertTrue(is_custom)

    # 2. Customer B has Kubbus price ₹11.
    def test_case_02_customer_b_price_configuration(self):
        set_customer_product_price(self.customer_b, self.product_kubbus, Decimal('11.00'))
        eff_price, is_custom, _ = get_effective_product_price(self.customer_b, self.product_kubbus)
        self.assertEqual(eff_price, Decimal('11.00'))
        self.assertTrue(is_custom)

    # 3. Billing Customer A automatically gets ₹10.
    def test_case_03_billing_customer_a_automatically_gets_10(self):
        set_customer_product_price(self.customer_a, self.product_kubbus, Decimal('10.00'))
        order = create_order_service(
            customer_id=str(self.customer_a.id),
            items_data=[{'product_id': str(self.product_kubbus.id), 'quantity': 100}],
            created_by=self.manager,
        )
        item = order.items.first()
        self.assertEqual(item.unit_price, Decimal('10.00'))
        self.assertEqual(item.subtotal, Decimal('1000.00'))
        self.assertEqual(order.total_amount, Decimal('1000.00'))

    # 4. Billing Customer B automatically gets ₹11.
    def test_case_04_billing_customer_b_automatically_gets_11(self):
        set_customer_product_price(self.customer_b, self.product_kubbus, Decimal('11.00'))
        order = create_order_service(
            customer_id=str(self.customer_b.id),
            items_data=[{'product_id': str(self.product_kubbus.id), 'quantity': 100}],
            created_by=self.manager,
        )
        item = order.items.first()
        self.assertEqual(item.unit_price, Decimal('11.00'))
        self.assertEqual(item.subtotal, Decimal('1100.00'))
        self.assertEqual(order.total_amount, Decimal('1100.00'))

    # 5. Authorized Manager can override one order price (e.g. ₹9.50) without changing permanent customer rate.
    def test_case_05_manager_price_override_on_order(self):
        set_customer_product_price(self.customer_a, self.product_kubbus, Decimal('10.00'))
        order = create_order_service(
            customer_id=str(self.customer_a.id),
            items_data=[{'product_id': str(self.product_kubbus.id), 'quantity': 100, 'unit_price': Decimal('9.50')}],
            created_by=self.manager,
        )
        item = order.items.first()
        self.assertEqual(item.unit_price, Decimal('9.50'))
        self.assertEqual(item.subtotal, Decimal('950.00'))
        self.assertEqual(order.total_amount, Decimal('950.00'))

        # Permanent customer price remains ₹10.00
        permanent_price, is_custom, _ = get_effective_product_price(self.customer_a, self.product_kubbus)
        self.assertEqual(permanent_price, Decimal('10.00'))

    # 6. Order history preserves the old price.
    def test_case_06_order_history_preserves_old_price(self):
        set_customer_product_price(self.customer_a, self.product_kubbus, Decimal('10.00'))
        order = create_order_service(
            customer_id=str(self.customer_a.id),
            items_data=[{'product_id': str(self.product_kubbus.id), 'quantity': 50}],
            created_by=self.manager,
        )
        old_item = order.items.first()
        self.assertEqual(old_item.unit_price, Decimal('10.00'))

        # Later, price increases to ₹12.50
        set_customer_product_price(self.customer_a, self.product_kubbus, Decimal('12.50'))

        # Reload order from DB
        order.refresh_from_db()
        old_item.refresh_from_db()
        self.assertEqual(old_item.unit_price, Decimal('10.00'))
        self.assertEqual(order.total_amount, Decimal('500.00'))

    # 7. Changing customer pricing does not modify old orders.
    def test_case_07_changing_customer_pricing_does_not_modify_old_orders(self):
        # Create order at ₹10
        set_customer_product_price(self.customer_a, self.product_kubbus, Decimal('10.00'))
        order_old = create_order_service(
            customer_id=str(self.customer_a.id),
            items_data=[{'product_id': str(self.product_kubbus.id), 'quantity': 20}],
            created_by=self.manager,
        )
        self.assertEqual(order_old.total_amount, Decimal('200.00'))

        # Update customer price to ₹15.00
        set_customer_product_price(self.customer_a, self.product_kubbus, Decimal('15.00'))

        # Create new order
        order_new = create_order_service(
            customer_id=str(self.customer_a.id),
            items_data=[{'product_id': str(self.product_kubbus.id), 'quantity': 20}],
            created_by=self.manager,
        )

        order_old.refresh_from_db()
        self.assertEqual(order_old.total_amount, Decimal('200.00'))
        self.assertEqual(order_new.total_amount, Decimal('300.00'))

    # 8. New customer can be created from billing via API.
    def test_case_08_new_customer_created_from_billing(self):
        self.client.force_authenticate(user=self.manager)
        response = self.client.post('/api/v1/customers/', {
            'name': 'Direct From Billing Shop',
            'owner_name': 'Hassan',
            'phone': '9847333333',
            'address': 'Near Bus Stand, Pandikkad',
            'route': str(self.route_pkd.id),
            'credit_limit': '5000.00',
            'notes': 'Created during morning dispatch billing',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Direct From Billing Shop')
        new_cust_id = response.data['id']
        self.assertTrue(Customer.objects.filter(id=new_cust_id).exists())

    # 9. New customer becomes selectable immediately for billing.
    def test_case_09_new_customer_selectable_immediately(self):
        self.client.force_authenticate(user=self.manager)
        create_resp = self.client.post('/api/v1/customers/', {
            'name': 'Immediate Billing Shop',
            'owner_name': 'Ismail',
            'phone': '9847444444',
            'address': 'Market Road',
            'route': str(self.route_pkd.id),
        })
        new_cust_id = create_resp.data['id']

        # Query customers list endpoint
        list_resp = self.client.get('/api/v1/customers/')
        cust_ids = [c['id'] for c in list_resp.data.get('results', list_resp.data)]
        self.assertIn(new_cust_id, cust_ids)

        # Place order immediately for new customer
        order_resp = self.client.post('/api/v1/orders/', {
            'customer_id': new_cust_id,
            'items': [{'product_id': str(self.product_kubbus.id), 'quantity': 30}],
        }, format='json')
        self.assertEqual(order_resp.status_code, status.HTTP_201_CREATED)

    # 10. Driver can create their own expense.
    def test_case_10_driver_can_create_own_expense(self):
        self.client.force_authenticate(user=self.driver_a_user)
        response = self.client.post('/api/v1/driver-expenses/', {
            'category': 'PETROL',
            'amount': '450.00',
            'date': '2026-09-26',
            'notes': '5L petrol at Pandikkad',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(str(response.data['driver']), str(self.driver_a.id))
        self.assertEqual(Decimal(str(response.data['amount'])), Decimal('450.00'))

    # 11. Driver cannot view another driver's expense.
    def test_case_11_driver_cannot_view_another_drivers_expense(self):
        expense_b = DriverExpense.objects.create(
            driver=self.driver_b,
            category=DriverExpense.Category.FOOD,
            amount=Decimal('150.00'),
            date=timezone.now().date(),
        )

        self.client.force_authenticate(user=self.driver_a_user)
        response = self.client.get(f'/api/v1/driver-expenses/{expense_b.id}/')
        # Expect 404 or 403: isolation guarantees Driver A cannot see Driver B's record
        self.assertIn(response.status_code, [status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN])

    # 12. Driver cannot modify another driver's expense.
    def test_case_12_driver_cannot_modify_another_drivers_expense(self):
        expense_b = DriverExpense.objects.create(
            driver=self.driver_b,
            category=DriverExpense.Category.PARKING,
            amount=Decimal('50.00'),
            date=timezone.now().date(),
        )

        self.client.force_authenticate(user=self.driver_a_user)
        response = self.client.patch(f'/api/v1/driver-expenses/{expense_b.id}/', {
            'amount': '100.00',
        })
        self.assertIn(response.status_code, [status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN])
        expense_b.refresh_from_db()
        self.assertEqual(expense_b.amount, Decimal('50.00'))

    # 13. Driver only sees assigned-route deliveries.
    def test_case_13_driver_only_sees_assigned_route_deliveries(self):
        order_pkd = create_order_service(
            customer_id=str(self.customer_a.id),
            items_data=[{'product_id': str(self.product_kubbus.id), 'quantity': 10}],
            created_by=self.manager,
        )
        order_prd = create_order_service(
            customer_id=str(self.customer_b.id),
            items_data=[{'product_id': str(self.product_kubbus.id), 'quantity': 10}],
            created_by=self.manager,
        )

        self.client.force_authenticate(user=self.driver_a_user)
        response = self.client.get('/api/v1/deliveries/')
        results = response.data.get('results', response.data)
        delivery_ids = [d['id'] for d in results]

        self.assertIn(str(order_pkd.delivery.id), delivery_ids)
        self.assertNotIn(str(order_prd.delivery.id), delivery_ids)

    # 14. Driver cannot access another route by changing an ID in the URL/API.
    def test_case_14_driver_cannot_access_unauthorized_route(self):
        self.client.force_authenticate(user=self.driver_a_user)
        # Attempt to access Route PRD directly (returns 404/403 preventing leakage)
        response = self.client.get(f'/api/v1/routes/{self.route_prd.id}/')
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    # 15. Owner can view all expenses.
    def test_case_15_owner_can_view_all_expenses(self):
        DriverExpense.objects.create(
            driver=self.driver_a,
            category=DriverExpense.Category.PETROL,
            amount=Decimal('500.00'),
            date=timezone.now().date(),
        )
        DriverExpense.objects.create(
            driver=self.driver_b,
            category=DriverExpense.Category.TOLL,
            amount=Decimal('120.00'),
            date=timezone.now().date(),
        )

        self.client.force_authenticate(user=self.owner)
        response = self.client.get('/api/v1/driver-expenses/')
        results = response.data.get('results', response.data)
        self.assertEqual(len(results), 2)

    # 16. Manager can view permitted expense information.
    def test_case_16_manager_can_view_expenses(self):
        DriverExpense.objects.create(
            driver=self.driver_a,
            category=DriverExpense.Category.FOOD,
            amount=Decimal('150.00'),
            date=timezone.now().date(),
        )

        self.client.force_authenticate(user=self.manager)
        response = self.client.get('/api/v1/driver-expenses/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        self.assertGreaterEqual(len(results), 1)

    # 17. Invalid price/quantity/expense values are rejected.
    def test_case_17_invalid_values_rejected(self):
        self.client.force_authenticate(user=self.manager)

        # Quantity <= 0
        resp_qty = self.client.post('/api/v1/orders/', {
            'customer_id': str(self.customer_a.id),
            'items': [{'product_id': str(self.product_kubbus.id), 'quantity': 0}],
        }, format='json')
        self.assertEqual(resp_qty.status_code, status.HTTP_400_BAD_REQUEST)

        # Price < 0
        resp_price = self.client.post(f'/api/v1/customers/{self.customer_a.id}/pricing/', {
            'product_id': str(self.product_kubbus.id),
            'price': '-5.00',
        })
        self.assertEqual(resp_price.status_code, status.HTTP_400_BAD_REQUEST)

        # Expense amount <= 0
        self.client.force_authenticate(user=self.driver_a_user)
        resp_exp = self.client.post('/api/v1/driver-expenses/', {
            'category': 'PETROL',
            'amount': '0.00',
            'date': '2026-09-26',
        })
        self.assertEqual(resp_exp.status_code, status.HTTP_400_BAD_REQUEST)

    # 18. Financial calculations use Decimal (never float).
    def test_case_18_financial_calculations_use_decimal(self):
        set_customer_product_price(self.customer_a, self.product_kubbus, Decimal('10.25'))
        order = create_order_service(
            customer_id=str(self.customer_a.id),
            items_data=[{'product_id': str(self.product_kubbus.id), 'quantity': 3}],
            created_by=self.manager,
        )
        self.assertIsInstance(order.total_amount, Decimal)
        self.assertEqual(order.total_amount, Decimal('30.75'))

    # 19. Payment records remain auditable with CreditTransaction ledger.
    def test_case_19_payment_and_credit_ledger_auditable(self):
        from apps.deliveries.services import complete_delivery_service
        # Order of ₹1200
        order = create_order_service(
            customer_id=str(self.customer_a.id),
            items_data=[{'product_id': str(self.product_kubbus.id), 'quantity': 100, 'unit_price': Decimal('12.00')}],
            created_by=self.manager,
        )
        # Fulfilling delivery triggers credit sale addition to customer ledger
        complete_delivery_service(
            delivery_id=order.delivery.id,
            recipient_name="Shop Staff",
            user=self.driver_a_user,
        )
        self.customer_a.refresh_from_db()
        self.assertEqual(self.customer_a.current_balance, Decimal('1200.00'))

        # Customer pays ₹500
        self.client.force_authenticate(user=self.manager)
        pay_resp = self.client.post('/api/v1/payments/', {
            'customer_id': str(self.customer_a.id),
            'amount': '500.00',
            'payment_method': 'CASH',
        })
        self.assertEqual(pay_resp.status_code, status.HTTP_201_CREATED)

        self.customer_a.refresh_from_db()
        self.assertEqual(self.customer_a.current_balance, Decimal('700.00'))

        # CreditTransaction records exist
        txs = CreditTransaction.objects.filter(customer=self.customer_a).order_by('created_at')
        self.assertEqual(txs.count(), 2)  # 1 CREDIT_SALE + 1 CASH_PAYMENT
        sale_tx = txs.filter(transaction_type=CreditTransaction.TransactionType.CREDIT_SALE).first()
        self.assertEqual(sale_tx.amount, Decimal('1200.00'))
        pay_tx = txs.filter(transaction_type=CreditTransaction.TransactionType.CASH_PAYMENT).first()
        self.assertEqual(pay_tx.amount, Decimal('-500.00'))
        self.assertEqual(pay_tx.balance_after, Decimal('700.00'))

    # 20. Dashboard totals come from actual database records (including net_collection = total_collected - today_expenses).
    def test_case_20_dashboard_totals_accurate(self):
        today = timezone.now().date()
        # Order ₹1000
        order = create_order_service(
            customer_id=str(self.customer_a.id),
            items_data=[{'product_id': str(self.product_kubbus.id), 'quantity': 100, 'unit_price': Decimal('10.00')}],
            created_by=self.manager,
        )
        # Payment ₹600
        Payment.objects.create(
            customer=self.customer_a,
            amount=Decimal('600.00'),
            payment_method=Payment.Method.CASH,
            collected_by=self.driver_a_user,
        )
        # Driver expense ₹150
        DriverExpense.objects.create(
            driver=self.driver_a,
            category=DriverExpense.Category.PETROL,
            amount=Decimal('150.00'),
            date=today,
        )

        self.client.force_authenticate(user=self.owner)
        response = self.client.get('/api/v1/reports/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(Decimal(str(response.data['today_sales'])), Decimal('1000.00'))
        self.assertEqual(Decimal(str(response.data['total_collected'])), Decimal('600.00'))
        self.assertEqual(Decimal(str(response.data['today_expenses'])), Decimal('150.00'))
        self.assertEqual(Decimal(str(response.data['net_collection'])), Decimal('450.00'))
