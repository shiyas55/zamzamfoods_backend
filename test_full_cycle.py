import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from decimal import Decimal
from django.utils import timezone
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.customers.models import Customer
from apps.products.models import Product
from apps.routes.models import Route, Driver, DriverShift
from apps.orders.models import Order
from apps.deliveries.models import Delivery
from apps.payments.models import Payment
from apps.credits.models import CreditTransaction

def run_test():
    print("==================================================")
    print("STARTING FULL END-TO-END BUSINESS LOGIC VERIFICATION")
    print("==================================================")

    # 1. Setup Clients
    manager = User.objects.get(username="manager")
    driver_user = User.objects.get(username="driver_pkd")
    driver_obj = Driver.objects.get(user=driver_user)
    
    manager_client = APIClient()
    manager_client.force_authenticate(user=manager)

    driver_client = APIClient()
    driver_client.force_authenticate(user=driver_user)

    # 2. Pick Customer and Product
    customer = Customer.objects.filter(route__name="Pandikkad").first()
    kubbus = Product.objects.get(code="KUB")
    romali = Product.objects.get(code="ROM")
    initial_balance = customer.current_balance
    print(f"Customer: {customer.name} (Route: {customer.route.name})")
    print(f"Initial Customer Outstanding Balance: Rs.{initial_balance}")

    # 3. Manager Places Wholesale Order
    # e.g., 20 ps Kubbus, 10 ps Romali
    order_data = {
        "customer": customer.id,
        "order_date": str(timezone.localdate()),
        "status": "CONFIRMED",
        "notes": "Full cycle test order",
        "items": [
            {
                "product": kubbus.id,
                "quantity": 20,
                "unit_price": "35.00"
            },
            {
                "product": romali.id,
                "quantity": 10,
                "unit_price": "45.00"
            }
        ]
    }
    print("\n--- STEP 1: Manager Places Wholesale Order ---")
    res_order = manager_client.post("/api/v1/orders/", order_data, format="json")
    assert res_order.status_code == 201, f"Order placement failed: {res_order.data}"
    order_id = res_order.data["id"]
    order_number = res_order.data["order_number"]
    total_amount = Decimal(str(res_order.data["total_amount"]))
    expected_amount = Decimal(20 * 35 + 10 * 45) # 700 + 450 = 1150
    print(f"Created Order: #{order_number} (ID: {order_id}), Total Amount: Rs.{total_amount}")
    assert total_amount == expected_amount, f"Expected Rs.{expected_amount}, got Rs.{total_amount}"

    # 4. Verify Delivery Generated & Assigned to Driver
    print("\n--- STEP 2: Verify Delivery Generation & Assignment ---")
    delivery = Delivery.objects.filter(order_id=order_id).first()
    assert delivery is not None, "Delivery was not auto-generated for confirmed order!"
    print(f"Delivery ID: {delivery.id}, Status: {delivery.status}")
    print(f"Assigned Driver: {delivery.driver.user.username if delivery.driver else 'None'}")
    assert delivery.driver == driver_obj, f"Delivery driver mismatch: expected {driver_obj}, got {delivery.driver}"

    # 5. Driver Day Open (Shift Stock Verification)
    print("\n--- STEP 3: Driver Opens Day & Verifies Stock ---")
    # Clean previous shift for today if needed for clean test
    shift, _ = DriverShift.objects.get_or_create(driver=driver_obj, date=timezone.localdate())
    open_payload = {
        "kubbus_loaded": 50, # 50 ps loaded
        "romali_loaded": 30, # 30 ps loaded
        "opening_notes": "Stock counted & verified in van."
    }
    res_open = driver_client.post("/api/v1/routes/driver_shift/open_day/", open_payload, format="json")
    assert res_open.status_code == 200, f"Driver open day failed: {res_open.data}"
    assert res_open.data["is_opened"] is True
    print(f"Driver Day Opened: Kubbus={res_open.data['kubbus_loaded']} ps, Romali={res_open.data['romali_loaded']} ps")

    # 6. Driver Views Deliveries (Driver Isolation Check)
    print("\n--- STEP 4: Driver Lists Deliveries (Isolation Check) ---")
    res_del_list = driver_client.get("/api/v1/deliveries/")
    assert res_del_list.status_code == 200
    my_del_ids = [d["id"] for d in res_del_list.data["results"] if "results" in res_del_list.data] if isinstance(res_del_list.data, dict) else [d["id"] for d in res_del_list.data]
    assert delivery.id in my_del_ids, "Driver cannot see assigned delivery!"
    print(f"Driver successfully fetched delivery list, assigned delivery {delivery.id} present.")

    # 7. Driver Completes Delivery (Customer gets goods)
    print("\n--- STEP 5: Driver Completes Delivery ---")
    complete_payload = {
        "recipient_name": "Shop Incharge",
        "notes": "Delivered fresh morning batch."
    }
    res_complete = driver_client.post(f"/api/v1/deliveries/{delivery.id}/complete/", complete_payload, format="json")
    assert res_complete.status_code == 200, f"Complete delivery failed: {res_complete.data}"
    assert res_complete.data["status"] == "DELIVERED"
    print(f"Delivery {delivery.id} marked DELIVERED successfully.")

    # Check Customer Balance & Ledger after delivery
    customer.refresh_from_db()
    print(f"Customer Balance after delivery (Credit Sale Rs.{total_amount} posted): Rs.{customer.current_balance}")
    assert customer.current_balance == initial_balance + total_amount, "Customer balance did not increase by order amount!"

    # 8. Driver Collects Payment for this Delivery (Cash Rs.1,150)
    print("\n--- STEP 6: Driver Collects Payment (Cash Rs.1,150) ---")
    pay_payload = {
        "customer": customer.id,
        "order": order_id,
        "amount": str(total_amount),
        "payment_method": "CASH",
        "notes": "Full payment collected upon delivery."
    }
    res_pay = driver_client.post("/api/v1/payments/", pay_payload, format="json")
    assert res_pay.status_code == 201, f"Payment collection failed: {res_pay.data}"
    payment_id = res_pay.data["id"]
    payment_number = res_pay.data["payment_number"]
    print(f"Payment recorded: #{payment_number} (ID: {payment_id}), Method: CASH, Amount: Rs.{res_pay.data['amount']}")

    # Check Customer Balance after payment
    customer.refresh_from_db()
    print(f"Customer Balance after payment: Rs.{customer.current_balance}")
    assert customer.current_balance == initial_balance, f"Customer balance should return to Rs.{initial_balance}, got Rs.{customer.current_balance}"

    # 9. Verify Manager Daily Summary & Collections View
    print("\n--- STEP 7: Verify Manager Payment Daily Summary & Collections ---")
    res_sum = manager_client.get("/api/v1/payments/daily_summary/")
    assert res_sum.status_code == 200
    print(f"Manager Daily Summary: Total Collected = Rs.{res_sum.data['total_collected']}, Cash = Rs.{res_sum.data['cash_total']}, UPI = Rs.{res_sum.data['upi_total']}, Count = {res_sum.data['count']}")
    assert Decimal(str(res_sum.data['total_collected'])) >= total_amount, "Daily summary did not include newly collected payment!"

    # 10. Verify Driver Shift Metrics
    print("\n--- STEP 8: Verify Driver Shift Metrics ---")
    res_shift = driver_client.get("/api/v1/routes/driver_shift/my_shift/")
    assert res_shift.status_code == 200
    metrics = res_shift.data.get("metrics", {})
    print(f"Driver Shift Metrics: Assigned Stops={metrics.get('assigned_stops')}, Delivered={metrics.get('delivered_stops')}, Delivered Kubbus={metrics.get('delivered_kubbus')} ps, Delivered Romali={metrics.get('delivered_romali')} ps")
    assert metrics.get("delivered_stops", 0) >= 1

    print("\n==================================================")
    print("ALL LOGICAL TESTS PASSED PERFECTLY!")
    print("==================================================")

if __name__ == "__main__":
    run_test()
