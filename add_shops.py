import os
import django
import random
from decimal import Decimal

# Initialize Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.customers.models import Customer
from apps.routes.models import Route

def clear_balances():
    print("Clearing all previous dues to zero...")
    Customer.objects.update(current_balance=Decimal("0.00"))
    print("Balances cleared!")

def add_shops():
    print("Fetching routes...")
    
    # Ensure routes exist or create them
    route_pmna, _ = Route.objects.get_or_create(name='pmna')
    route_melatue, _ = Route.objects.get_or_create(name='melatue')
    
    print("Adding 50 shops for pmna...")
    pmna_shops = []
    for i in range(1, 51):
        pmna_shops.append(Customer(
            name=f"Pmna Shop {i}",
            owner_name=f"Owner {i}",
            phone=f"900000{i:04d}",
            address=f"Street {i}, Perinthalmanna",
            route=route_pmna,
            current_balance=Decimal("0.00"),
            credit_limit=Decimal("5000.00")
        ))
    Customer.objects.bulk_create(pmna_shops)
    
    print("Adding 50 shops for melatue...")
    melatue_shops = []
    for i in range(1, 51):
        melatue_shops.append(Customer(
            name=f"Melattur Shop {i}",
            owner_name=f"Owner M{i}",
            phone=f"800000{i:04d}",
            address=f"Main Road {i}, Melattur",
            route=route_melatue,
            current_balance=Decimal("0.00"),
            credit_limit=Decimal("5000.00")
        ))
    Customer.objects.bulk_create(melatue_shops)
    
    print("100 Dynamic shops added successfully!")

if __name__ == '__main__':
    clear_balances()
    add_shops()
