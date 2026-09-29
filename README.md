# Zamzam Foods — Backend Architecture

## Overview
Modular Django REST Framework application structured into domain services:
- `apps/accounts`: Custom User model with OWNER, MANAGER, and DRIVER roles; SimpleJWT authentication.
- `apps/routes`: Routes (Pandikkad, Perundurai, Melattur) and Driver profiles.
- `apps/customers`: Customer shops (~200 shops) with credit limits and current balances.
- `apps/products`: Product catalog (Kubbus, Romali).
- `apps/orders`: Order creation, line items, and atomic status updates.
- `apps/deliveries`: Driver dispatch management and delivery completion with customer signature/recipient logs.
- `apps/payments`: Payment collection tracking (Cash & GPay/UPI).
- `apps/credits`: Immutable credit ledger tracking debts, sales, collections, and authorized adjustments.
- `apps/reports`: Aggregation endpoints for executive and operational dashboards.
- `apps/common`: Abstract base models (`TimeStampedUUIDModel`), standardized exception handling, and custom role permissions.

## Running Tests
```bash
python manage.py test tests
```
