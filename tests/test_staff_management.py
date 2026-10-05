from decimal import Decimal
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from apps.accounts.models import User, StaffMember, StaffAttendance, StaffPayout

class StaffManagementTests(APITestCase):
    """
    Automated integration tests for Staff Management:
    - Worker profiles (no login account) & login profiles
    - Joined date tenure wage slabs (₹400 / ₹500 / ₹600) and custom wage
    - Daily attendance (Full, Half, Leave) with wage calculation
    - Bulk attendance roll-call
    - Staff payouts and ledger balance calculation
    """

    def setUp(self):
        self.owner = User.objects.create_user(
            username="test_owner",
            password="password123",
            role=User.Role.OWNER,
            first_name="Owner",
            last_name="Test"
        )
        self.manager = User.objects.create_user(
            username="test_manager",
            password="password123",
            role=User.Role.MANAGER,
            first_name="Manager",
            last_name="Test"
        )
        self.driver_user = User.objects.create_user(
            username="test_driver_user",
            password="password123",
            role=User.Role.DRIVER,
            first_name="Driver",
            last_name="User"
        )

        self.client.force_authenticate(user=self.owner)

    def test_create_worker_staff_without_login_account(self):
        """Creates a staff member who has NO login account / no system role."""
        resp = self.client.post(
            "/api/v1/auth/staff/",
            {
                "full_name": "Hamza Baker",
                "phone_number": "9876543210",
                "designation": "Bakery Chef",
                "joined_date": str(timezone.localdate()),
                "wage_type": "DEFAULT_SLAB",
            }
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["full_name"], "Hamza Baker")
        self.assertFalse(resp.data["has_login_account"])
        self.assertIsNone(resp.data["user"])
        # Brand new joiner should be ₹400/day
        self.assertEqual(Decimal(resp.data["current_daily_wage"]), Decimal("400.00"))

    def test_create_staff_with_linked_login_account(self):
        """Creates a staff member linked to an existing login User account."""
        resp = self.client.post(
            "/api/v1/auth/staff/",
            {
                "full_name": "Driver User",
                "phone_number": "9876543211",
                "designation": "Delivery Driver",
                "joined_date": str(timezone.localdate()),
                "wage_type": "DEFAULT_SLAB",
                "user": str(self.driver_user.id),
            }
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp.data["has_login_account"])
        self.assertEqual(resp.data["user"], self.driver_user.id)

    def test_joined_date_tenure_wage_slabs(self):
        """
        Verifies automatic tenure wage slabs:
        - < 2 months (< 60 days): ₹400
        - 2 to 6 months (60 - 180 days): ₹500
        - 6+ months (180+ days): ₹600
        """
        today = timezone.localdate()

        # 1. New staff (20 days ago) -> ₹400
        staff_new = StaffMember.objects.create(
            full_name="Staff New",
            joined_date=today - timezone.timedelta(days=20),
            wage_type=StaffMember.WageType.DEFAULT_SLAB
        )
        self.assertEqual(staff_new.current_daily_wage, Decimal("400.00"))

        # 2. Intermediate staff (90 days ago) -> ₹500
        staff_mid = StaffMember.objects.create(
            full_name="Staff Mid",
            joined_date=today - timezone.timedelta(days=90),
            wage_type=StaffMember.WageType.DEFAULT_SLAB
        )
        self.assertEqual(staff_mid.current_daily_wage, Decimal("500.00"))

        # 3. Senior staff (200 days ago) -> ₹600
        staff_sr = StaffMember.objects.create(
            full_name="Staff Senior",
            joined_date=today - timezone.timedelta(days=200),
            wage_type=StaffMember.WageType.DEFAULT_SLAB
        )
        self.assertEqual(staff_sr.current_daily_wage, Decimal("600.00"))

        # 4. Custom wage staff -> ₹750 override
        staff_custom = StaffMember.objects.create(
            full_name="Staff Custom",
            joined_date=today - timezone.timedelta(days=10),
            wage_type=StaffMember.WageType.CUSTOM,
            custom_daily_wage=Decimal("750.00")
        )
        self.assertEqual(staff_custom.current_daily_wage, Decimal("750.00"))

    def test_daily_attendance_and_wage_calculation(self):
        """Attendance marks Full (100%), Half (50%), and Leave (0)."""
        today = timezone.localdate()
        # 90 days tenure = ₹500/day
        staff = StaffMember.objects.create(
            full_name="Rashid Helper",
            joined_date=today - timezone.timedelta(days=90),
            wage_type=StaffMember.WageType.DEFAULT_SLAB
        )

        # Full day -> ₹500
        att_full = StaffAttendance.objects.create(
            staff=staff,
            date=today - timezone.timedelta(days=2),
            status=StaffAttendance.Status.FULL,
            marked_by=self.owner
        )
        self.assertEqual(att_full.daily_wage, Decimal("500.00"))

        # Half day -> ₹250
        att_half = StaffAttendance.objects.create(
            staff=staff,
            date=today - timezone.timedelta(days=1),
            status=StaffAttendance.Status.HALF,
            marked_by=self.owner
        )
        self.assertEqual(att_half.daily_wage, Decimal("250.00"))

        # Leave -> ₹0
        att_leave = StaffAttendance.objects.create(
            staff=staff,
            date=today,
            status=StaffAttendance.Status.LEAVE,
            marked_by=self.owner
        )
        self.assertEqual(att_leave.daily_wage, Decimal("0.00"))

    def test_bulk_attendance_and_daily_sheet_endpoint(self):
        """Tests the roll-call sheet and bulk-save attendance endpoint."""
        today = timezone.localdate()
        s1 = StaffMember.objects.create(full_name="Worker A", joined_date=today - timezone.timedelta(days=30))
        s2 = StaffMember.objects.create(full_name="Worker B", joined_date=today - timezone.timedelta(days=100))

        # Bulk save attendance for today
        bulk_resp = self.client.post(
            "/api/v1/auth/staff-attendance/bulk-save/",
            {
                "date": str(today),
                "attendances": [
                    {"staff_id": str(s1.id), "status": "FULL", "notes": "On time"},
                    {"staff_id": str(s2.id), "status": "HALF", "notes": "Half day morning"},
                ]
            },
            format="json"
        )
        self.assertEqual(bulk_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(bulk_resp.data["count"], 2)

        # Fetch daily sheet
        sheet_resp = self.client.get(f"/api/v1/auth/staff-attendance/daily-sheet/?date={today}")
        self.assertEqual(sheet_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(sheet_resp.data["marked_count"], 2)

    def test_staff_payout_and_ledger_balance(self):
        """Records attendance and payouts, verifying running ledger calculation."""
        today = timezone.localdate()
        # Daily rate = ₹500
        staff = StaffMember.objects.create(
            full_name="Karim Baker",
            joined_date=today - timezone.timedelta(days=90),
            wage_type=StaffMember.WageType.DEFAULT_SLAB
        )

        # 3 full days of work = 3 * ₹500 = ₹1500
        for i in range(1, 4):
            StaffAttendance.objects.create(
                staff=staff,
                date=today - timezone.timedelta(days=i),
                status=StaffAttendance.Status.FULL,
                marked_by=self.owner
            )

        # Give ₹600 cash advance
        payout_resp = self.client.post(
            "/api/v1/auth/staff-payouts/",
            {
                "staff": str(staff.id),
                "amount": "600.00",
                "payout_type": "ADVANCE",
                "payment_method": "CASH",
                "date": str(today),
                "notes": "Emergency cash advance"
            }
        )
        self.assertEqual(payout_resp.status_code, status.HTTP_201_CREATED)

        # Check ledger
        ledger_resp = self.client.get(f"/api/v1/auth/staff/{staff.id}/ledger/")
        self.assertEqual(ledger_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(ledger_resp.data["total_earned"]), Decimal("1500.00"))
        self.assertEqual(Decimal(ledger_resp.data["total_paid"]), Decimal("600.00"))
        self.assertEqual(Decimal(ledger_resp.data["balance_due"]), Decimal("900.00"))

    def test_driver_auto_sync_to_staff_member(self):
        """Verifies that creating a Driver automatically creates a StaffMember as 'Staff Driver'."""
        resp = self.client.post(
            "/api/v1/drivers/",
            {
                "name": "Ilyas Driver",
                "phone_number": "9847012399",
                "vehicle_number": "KL-10-AB-1234",
                "license_number": "DL123456",
            }
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        # Check StaffMember auto-created
        staff = StaffMember.objects.filter(full_name="Ilyas Driver").first()
        self.assertIsNotNone(staff)
        self.assertEqual(staff.designation, "Staff Driver")
        self.assertTrue(staff.has_login_account)
        self.assertEqual(staff.phone_number, "9847012399")

