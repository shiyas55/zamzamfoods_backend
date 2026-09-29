from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User
from apps.customers.models import Customer
from apps.routes.models import Route
from apps.products.models import Product
from apps.common.models import SystemSettings

class SystemSettingsTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            username="test_owner_admin",
            password="OwnerPassword123!",
            role=User.Role.OWNER,
            email="owner@zamzam.test"
        )
        self.manager = User.objects.create_user(
            username="test_manager_user",
            password="ManagerPassword123!",
            role=User.Role.MANAGER,
            email="manager@zamzam.test"
        )
        self.driver_user = User.objects.create_user(
            username="test_driver_user",
            password="DriverPassword123!",
            role=User.Role.DRIVER,
            email="driver@zamzam.test"
        )
        self.route = Route.objects.create(name="Route S", code="RTS")
        self.customer = Customer.objects.create(
            name="Settings Test Customer",
            phone="9800099999",
            route=self.route,
            credit_limit=Decimal("5000.00")
        )
        self.product = Product.objects.create(
            name="Kubbus Test",
            code="KUB-T",
            unit_price=Decimal("10.00")
        )

    def test_settings_retrieval(self):
        # Unauthenticated retrieval returns public settings
        res = self.client.get("/api/v1/settings/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("is_whatsapp_enabled", res.data)
        self.assertIn("is_self_order_enabled", res.data)
        self.assertIn("business_name", res.data)
        self.assertIn("phone_number", res.data)

        # Owner gets full settings
        self.client.force_authenticate(user=self.owner)
        res_owner = self.client.get("/api/v1/settings/")
        self.assertEqual(res_owner.status_code, status.HTTP_200_OK)
        self.assertIn("id", res_owner.data)

    def test_admin_only_write_permission(self):
        # 1. Driver attempt to update settings MUST be forbidden (403)
        self.client.force_authenticate(user=self.driver_user)
        res_driver = self.client.patch("/api/v1/settings/", {"is_whatsapp_enabled": False})
        self.assertEqual(res_driver.status_code, status.HTTP_403_FORBIDDEN)

        # 2. Manager attempt to update settings MUST be forbidden (403)
        self.client.force_authenticate(user=self.manager)
        res_mgr = self.client.patch("/api/v1/settings/", {"is_whatsapp_enabled": False})
        self.assertEqual(res_mgr.status_code, status.HTTP_403_FORBIDDEN)

        # 3. Anonymous attempt to update settings MUST be forbidden (403)
        self.client.force_authenticate(user=None)
        res_anon = self.client.patch("/api/v1/settings/", {"is_whatsapp_enabled": False})
        self.assertEqual(res_anon.status_code, status.HTTP_403_FORBIDDEN)

        # 4. Owner / Admin CAN successfully update GST, phone, and feature toggles
        self.client.force_authenticate(user=self.owner)
        payload = {
            "business_name": "Zamzam Bakery & Foods Kerala",
            "gst_number": "32AABCU9603R1ZX",
            "phone_number": "+91 98470 55555",
            "is_whatsapp_enabled": False,
            "is_self_order_enabled": False,
            "invoice_footer_notes": "Official Zamzam Tax Invoice. Fresh Rotis."
        }
        res_owner = self.client.patch("/api/v1/settings/", payload, format="json")
        self.assertEqual(res_owner.status_code, status.HTTP_200_OK)
        self.assertEqual(res_owner.data["gst_number"], "32AABCU9603R1ZX")
        self.assertEqual(res_owner.data["phone_number"], "+91 98470 55555")
        self.assertFalse(res_owner.data["is_whatsapp_enabled"])
        self.assertFalse(res_owner.data["is_self_order_enabled"])

        # Check DB updated
        settings_db = SystemSettings.get_settings()
        self.assertEqual(settings_db.gst_number, "32AABCU9603R1ZX")
        self.assertFalse(settings_db.is_whatsapp_enabled)
        self.assertFalse(settings_db.is_self_order_enabled)

    def test_self_order_toggle_enforcement(self):
        # Disable self order
        settings_db = SystemSettings.get_settings()
        settings_db.is_self_order_enabled = False
        settings_db.save()

        # Customer tries to open link -> 403 Forbidden
        self.client.force_authenticate(user=None)
        get_res = self.client.get(f"/api/v1/public/customer-order/{self.customer.id}/")
        self.assertEqual(get_res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("error", get_res.data)

        # Customer tries to submit order -> 403 Forbidden
        post_res = self.client.post(
            f"/api/v1/public/customer-order/{self.customer.id}/",
            {"items": [{"product_id": str(self.product.id), "quantity": 10}]},
            format="json"
        )
        self.assertEqual(post_res.status_code, status.HTTP_403_FORBIDDEN)

        # Re-enable self order
        settings_db.is_self_order_enabled = True
        settings_db.save()

        # Now GET succeeds
        get_res_ok = self.client.get(f"/api/v1/public/customer-order/{self.customer.id}/")
        self.assertEqual(get_res_ok.status_code, status.HTTP_200_OK)

        # POST succeeds
        post_res_ok = self.client.post(
            f"/api/v1/public/customer-order/{self.customer.id}/",
            {"items": [{"product_id": str(self.product.id), "quantity": 10}]},
            format="json"
        )
        self.assertEqual(post_res_ok.status_code, status.HTTP_201_CREATED)

    def test_maintenance_mode_enforcement(self):
        # 1. By default, maintenance mode is OFF
        settings_db = SystemSettings.get_settings()
        self.assertFalse(settings_db.is_maintenance_mode)

        # Manager can access orders normally
        self.client.force_authenticate(user=self.manager)
        res_orders = self.client.get("/api/v1/orders/")
        self.assertEqual(res_orders.status_code, status.HTTP_200_OK)

        # 2. Owner turns maintenance mode ON
        self.client.force_authenticate(user=self.owner)
        patch_res = self.client.patch("/api/v1/settings/", {
            "is_maintenance_mode": True,
            "maintenance_message": "Upgrading server infrastructure for 30 minutes."
        }, format="json")
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertTrue(patch_res.data["is_maintenance_mode"])

        # 3. Manager is blocked with 503 Service Unavailable
        self.client.force_authenticate(user=self.manager)
        res_mgr_blocked = self.client.get("/api/v1/orders/")
        self.assertEqual(res_mgr_blocked.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn("Upgrading server infrastructure", res_mgr_blocked.json()["maintenance_message"])

        # 4. Driver is blocked with 503 Service Unavailable
        self.client.force_authenticate(user=self.driver_user)
        res_driver_blocked = self.client.get("/api/v1/deliveries/")
        self.assertEqual(res_driver_blocked.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

        # 5. Public customer portal is blocked with 503
        self.client.force_authenticate(user=None)
        res_public_blocked = self.client.get(f"/api/v1/public/customer-order/{self.customer.id}/")
        self.assertEqual(res_public_blocked.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

        # 6. Auth endpoints & settings endpoint remain accessible
        res_settings_public = self.client.get("/api/v1/settings/")
        self.assertEqual(res_settings_public.status_code, status.HTTP_200_OK)
        self.assertTrue(res_settings_public.data["is_maintenance_mode"])

        # 7. Owner CAN still access all protected endpoints and turn maintenance mode back OFF
        self.client.force_authenticate(user=self.owner)
        res_owner_orders = self.client.get("/api/v1/orders/")
        self.assertEqual(res_owner_orders.status_code, status.HTTP_200_OK)

        turn_off_res = self.client.patch("/api/v1/settings/", {
            "is_maintenance_mode": False
        }, format="json")
        self.assertEqual(turn_off_res.status_code, status.HTTP_200_OK)
        self.assertFalse(turn_off_res.data["is_maintenance_mode"])

        # 8. Manager access restored
        self.client.force_authenticate(user=self.manager)
        res_mgr_restored = self.client.get("/api/v1/orders/")
        self.assertEqual(res_mgr_restored.status_code, status.HTTP_200_OK)

    def test_whatsapp_upgrade_plan_lock_and_key(self):
        from django.utils import timezone
        import datetime

        # 1. Owner locks WhatsApp feature
        self.client.force_authenticate(user=self.owner)
        lock_res = self.client.patch("/api/v1/settings/", {
            "whatsapp_is_locked": True,
            "is_whatsapp_enabled": False,
        }, format="json")
        self.assertEqual(lock_res.status_code, status.HTTP_200_OK)
        self.assertTrue(lock_res.data["whatsapp_is_locked"])
        self.assertFalse(lock_res.data["is_whatsapp_enabled"])

        # Check model property
        settings_db = SystemSettings.get_settings()
        self.assertFalse(settings_db.is_whatsapp_active)

        # 2. Owner unlocks with 365-day upgrade key
        future_expiry = (timezone.now() + datetime.timedelta(days=365)).isoformat()
        unlock_res = self.client.patch("/api/v1/settings/", {
            "whatsapp_is_locked": False,
            "whatsapp_plan_name": "1-Year Enterprise Annual Pass",
            "whatsapp_plan_expires_at": future_expiry,
            "whatsapp_license_key": "ZAMZAM-WA-365D",
            "is_whatsapp_enabled": True,
        }, format="json")
        self.assertEqual(unlock_res.status_code, status.HTTP_200_OK)
        self.assertFalse(unlock_res.data["whatsapp_is_locked"])
        self.assertEqual(unlock_res.data["whatsapp_plan_name"], "1-Year Enterprise Annual Pass")
        self.assertEqual(unlock_res.data["whatsapp_license_key"], "ZAMZAM-WA-365D")
        self.assertTrue(unlock_res.data["is_whatsapp_enabled"])

        # Check model property with valid future expiry
        settings_db.refresh_from_db()
        self.assertTrue(settings_db.is_whatsapp_active)

        # 3. If plan expired in past, is_whatsapp_active returns False
        settings_db.whatsapp_plan_expires_at = timezone.now() - datetime.timedelta(days=1)
        settings_db.save()
        self.assertFalse(settings_db.is_whatsapp_active)


