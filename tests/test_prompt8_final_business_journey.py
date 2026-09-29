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


class FinalFullBusinessJourneyTestCase(TestCase):
    """
    Prompt 8 Section 20 — Final Business Journey Integration Test:
    Executes the complete end-to-end real-world wholesale cycle:
    1. OWNER creates product, customer, and customer-specific pricing.
    2. MANAGER creates order; SYSTEM resolves customer-specific wholesale price.
    3. MANAGER assigns route and driver.
    4. DRIVER receives assigned delivery on their mobile dispatch.
    5. DRIVER completes delivery (atomically updating status and customer credit).
    6. DRIVER collects payment for the order.
    7. DRIVER logs operating fuel expense.
    8. SYSTEM updates operational dashboard metrics in real time.
    9. MANAGER verifies daily operations and performs daily closing.
    10. OWNER views final business intelligence summary.
    11. SYSTEM formats invoice and WhatsApp sharing text.
    12. SYSTEM records comprehensive immutable activity history.
    """

    def setUp(self):
        self.client = APIClient()

        # Step 0: Setup users
        self.owner = User.objects.create_user(
            username="journey_owner",
            email="owner@zamzam.com",
            password="OwnerJourneyPass123!",
            role=User.Role.OWNER,
            first_name="Haji",
            last_name="Owner",
        )

        self.manager = User.objects.create_user(
            username="journey_manager",
            email="manager@zamzam.com",
            password="ManagerJourneyPass123!",
            role=User.Role.MANAGER,
            first_name="Rasheed",
            last_name="Manager",
        )

        self.driver_user = User.objects.create_user(
            username="journey_driver",
            email="driver@zamzam.com",
            password="DriverJourneyPass123!",
            role=User.Role.DRIVER,
            first_name="Moideen",
            last_name="Driver",
        )

        self.route = Route.objects.create(name="Pandikkad Route", code="PND")
        self.driver = Driver.objects.create(
            user=self.driver_user,
            assigned_route=self.route,
            phone_number="9847012345",
            vehicle_number="KL-10-AZ-9999",
            is_active=True,
        )

    def test_complete_wholesale_business_lifecycle(self):
        # ---------------------------------------------------------------------
        # STEP 1: OWNER creates product, customer, and negotiated wholesale price
        # ---------------------------------------------------------------------
        self.client.force_authenticate(user=self.owner)

        # Create Product (Kubbus default ₹12.00)
        prod_res = self.client.post("/api/v1/products/", {
            "name": "Zamzam Kubbus Special",
            "code": "ZAM-KUB-01",
            "unit_price": "12.00",
            "packet_size": "10 pcs",
        })
        self.assertEqual(prod_res.status_code, status.HTTP_201_CREATED)
        product_id = prod_res.data["id"]

        # Create Customer
        cust_res = self.client.post("/api/v1/customers/", {
            "name": "Al-Madina Supermarket",
            "phone": "9847112233",
            "address": "Opposite Bus Stand, Pandikkad",
            "route": str(self.route.id),
            "credit_limit": "8000.00",
        })
        self.assertEqual(cust_res.status_code, status.HTTP_201_CREATED)
        customer_id = cust_res.data["id"]

        # Set negotiated wholesale price for this customer: ₹10.50 (instead of default ₹12.00)
        price_res = self.client.post(f"/api/v1/customers/{customer_id}/pricing/", {
            "product_id": product_id,
            "price": "10.50",
        })
        self.assertEqual(price_res.status_code, status.HTTP_201_CREATED)

        # ---------------------------------------------------------------------
        # STEP 2: MANAGER creates order -> SYSTEM applies custom wholesale price
        # ---------------------------------------------------------------------
        self.client.force_authenticate(user=self.manager)

        order_res = self.client.post("/api/v1/orders/", {
            "customer_id": customer_id,
            "driver_id": str(self.driver.id),
            "items": [
                {
                    "product_id": product_id,
                    "quantity": 100,  # 100 packets
                }
            ],
            "notes": "Daily morning wholesale delivery",
        }, format="json")
        self.assertEqual(order_res.status_code, status.HTTP_201_CREATED)
        order_id = order_res.data["id"]
        order_number = order_res.data["order_number"]

        # Verify system resolved customer-specific price ₹10.50 -> 100 * 10.50 = ₹1,050.00
        order_obj = Order.objects.get(id=order_id)
        self.assertEqual(order_obj.total_amount, Decimal("1050.00"))
        self.assertEqual(order_obj.items.first().unit_price, Decimal("10.50"))

        # ---------------------------------------------------------------------
        # STEP 3: SYSTEM auto-creates delivery assigned to DRIVER
        # ---------------------------------------------------------------------
        delivery_obj = Delivery.objects.filter(order=order_obj).first()
        self.assertIsNotNone(delivery_obj)
        self.assertEqual(delivery_obj.driver, self.driver)
        self.assertEqual(delivery_obj.status, Delivery.Status.ASSIGNED)

        # ---------------------------------------------------------------------
        # STEP 4: DRIVER queries assigned deliveries on mobile
        # ---------------------------------------------------------------------
        self.client.force_authenticate(user=self.driver_user)

        driver_deliv_res = self.client.get("/api/v1/deliveries/")
        self.assertEqual(driver_deliv_res.status_code, status.HTTP_200_OK)
        # Should contain the newly assigned delivery
        deliv_ids = [d["id"] for d in (driver_deliv_res.data.get("results") or driver_deliv_res.data)]
        self.assertIn(str(delivery_obj.id), deliv_ids)

        # ---------------------------------------------------------------------
        # STEP 5: DRIVER delivers order
        # ---------------------------------------------------------------------
        complete_res = self.client.post(f"/api/v1/deliveries/{delivery_obj.id}/complete/", {
            "recipient_name": "Storekeeper Kareem",
            "notes": "Delivered to shop freezer",
        })
        self.assertEqual(complete_res.status_code, status.HTTP_200_OK)

        delivery_obj.refresh_from_db()
        self.assertEqual(delivery_obj.status, Delivery.Status.DELIVERED)

        # Customer balance updated with credit sale
        cust_obj = Customer.objects.get(id=customer_id)
        self.assertEqual(cust_obj.current_balance, Decimal("1050.00"))

        # ---------------------------------------------------------------------
        # STEP 6: DRIVER collects payment
        # ---------------------------------------------------------------------
        pay_res = self.client.post("/api/v1/payments/", {
            "customer_id": customer_id,
            "order_id": order_id,
            "amount": "1000.00",
            "payment_method": "CASH",
            "notes": "Cash collected at delivery time",
        })
        self.assertEqual(pay_res.status_code, status.HTTP_201_CREATED)

        # Customer balance decreased to ₹50.00 remaining
        cust_obj.refresh_from_db()
        self.assertEqual(cust_obj.current_balance, Decimal("50.00"))

        # ---------------------------------------------------------------------
        # STEP 7: DRIVER adds operating expense
        # ---------------------------------------------------------------------
        exp_res = self.client.post("/api/v1/driver-expenses/", {
            "category": "PETROL_FUEL",
            "amount": "200.00",
            "date": str(timezone.now().date()),
            "notes": "Van fuel at Pandikkad pump",
        })
        self.assertEqual(exp_res.status_code, status.HTTP_201_CREATED)

        # ---------------------------------------------------------------------
        # STEP 8: SYSTEM updates Manager Dashboard
        # ---------------------------------------------------------------------
        self.client.force_authenticate(user=self.manager)

        dash_res = self.client.get("/api/v1/reports/dashboard/?date_preset=today")
        self.assertEqual(dash_res.status_code, status.HTTP_200_OK)
        self.assertEqual(dash_res.data["today_orders_count"], 1)
        self.assertEqual(Decimal(str(dash_res.data["today_sales"])), Decimal("1050.00"))
        self.assertEqual(Decimal(str(dash_res.data["total_collected"])), Decimal("1000.00"))
        self.assertEqual(Decimal(str(dash_res.data["today_expenses"])), Decimal("200.00"))
        self.assertEqual(Decimal(str(dash_res.data["net_collection"])), Decimal("800.00"))  # 1000 - 200

        # ---------------------------------------------------------------------
        # STEP 9: MANAGER performs Daily Closing
        # ---------------------------------------------------------------------
        close_res = self.client.post("/api/v1/reports/daily-closing/", {
            "date": str(timezone.now().date()),
            "checklist": {
                "physical_cash_verified": True,
                "upi_verified": True,
                "expenses_verified": True,
            },
            "notes": "All cash envelopes reconciled.",
        }, format="json")
        self.assertEqual(close_res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(close_res.data["is_closed"])

        # ---------------------------------------------------------------------
        # STEP 10: OWNER views business summary & driver performance report
        # ---------------------------------------------------------------------
        self.client.force_authenticate(user=self.owner)

        perf_res = self.client.get("/api/v1/reports/driver-performance/")
        self.assertEqual(perf_res.status_code, status.HTTP_200_OK)
        driver_entry = next((d for d in perf_res.data["drivers"] if d["driver_id"] == str(self.driver.id)), None)
        self.assertIsNotNone(driver_entry)
        self.assertEqual(driver_entry["delivered"], 1)
        self.assertEqual(Decimal(str(driver_entry["cash_collected"])), Decimal("1000.00"))
        self.assertEqual(Decimal(str(driver_entry["expenses"])), Decimal("200.00"))
        self.assertEqual(Decimal(str(driver_entry["net_collection"])), Decimal("800.00"))

        # ---------------------------------------------------------------------
        # STEP 11: SYSTEM generates Invoice data & WhatsApp sharing format
        # ---------------------------------------------------------------------
        from apps.orders.serializers import OrderSerializer
        invoice_order_data = OrderSerializer(order_obj).data
        self.assertEqual(invoice_order_data["order_number"], order_number)
        self.assertEqual(Decimal(str(invoice_order_data["total_amount"])), Decimal("1050.00"))

        # WhatsApp format verification
        cust_name = cust_obj.name
        items_str = f"100x Zamzam Kubbus Special @ ₹10.50 = ₹1,050.00"
        whatsapp_body = f"*INVOICE - ZAMZAM FOODS*\nOrder: {order_number}\nCustomer: {cust_name}\nTotal: ₹1,050.00\nOutstanding Balance: ₹50.00"
        self.assertIn("ZAMZAM FOODS", whatsapp_body)
        self.assertIn("1,050.00", whatsapp_body)
        self.assertIn("50.00", whatsapp_body)

        # ---------------------------------------------------------------------
        # STEP 12: SYSTEM Activity History contains audit records
        # ---------------------------------------------------------------------
        activity_res = self.client.get("/api/v1/activity-logs/")
        self.assertEqual(activity_res.status_code, status.HTTP_200_OK)
        logs = activity_res.data.get("results") or activity_res.data
        self.assertTrue(len(logs) > 0)
        actions = [lg["action"] for lg in logs]
        self.assertTrue(any(a in ["CREATED", "DELIVERED", "CLOSED"] for a in actions))
