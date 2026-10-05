from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.common.models import TimeStampedUUIDModel

class Route(TimeStampedUUIDModel):
    """
    Delivery routes operated by Zamzam Foods (e.g. Pandikkad, Perundurai, Melattur).
    """
    name = models.CharField(max_length=100, unique=True, help_text="Route name (e.g. Pandikkad)")
    code = models.CharField(max_length=20, unique=True, help_text="Short route code (e.g. PKD)")
    description = models.TextField(blank=True, help_text="Geographical or delivery notes")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Delivery Route"
        verbose_name_plural = "Delivery Routes"

    def __str__(self):
        return f"{self.name} ({self.code})"


class Driver(TimeStampedUUIDModel):
    """
    Driver profile linking accounts.User to their assigned route and delivery vehicle.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="driver_profile"
    )
    assigned_route = models.ForeignKey(
        Route,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="drivers",
        help_text="Primary territory/route assigned to this driver"
    )
    phone_number = models.CharField(max_length=20, blank=True)
    vehicle_number = models.CharField(max_length=30, blank=True, help_text="Vehicle registration number")
    license_number = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["user__first_name", "user__username"]
        verbose_name = "Staff Driver Profile"
        verbose_name_plural = "Staff Driver Profiles"

    @property
    def driver_name(self):
        if self.user:
            return self.user.get_full_name() or self.user.username
        return "Staff Driver"

    def __str__(self):
        full = self.driver_name
        route_name = self.assigned_route.name if self.assigned_route else "Unassigned"
        return f"{full} (Staff Driver) - Route: {route_name}"

    def sync_staff_profile(self):
        """
        Synchronizes this Driver with an accounts.StaffMember profile
        so the driver seamlessly participates in Staff Attendance,
        Daily Wage calculations, and Payout ledgers as 'Staff Driver'.
        """
        if not self.user:
            return None
        from apps.accounts.models import StaffMember
        name = self.driver_name
        phone = self.phone_number or self.user.phone_number or ""
        joined = self.user.date_joined.date() if self.user.date_joined else timezone.localdate()

        staff, created = StaffMember.objects.get_or_create(
            user=self.user,
            defaults={
                "full_name": name,
                "phone_number": phone,
                "role_type": "STAFF",
                "designation": "Staff Driver",
                "joined_date": joined,
                "is_active": self.is_active,
                "wage_type": StaffMember.WageType.DEFAULT_SLAB,
            }
        )
        if not created:
            updated = False
            if getattr(staff, "role_type", None) != "STAFF":
                staff.role_type = "STAFF"
                updated = True
            if staff.full_name != name:
                staff.full_name = name
                updated = True
            if phone and staff.phone_number != phone:
                staff.phone_number = phone
                updated = True
            if staff.is_active != self.is_active:
                staff.is_active = self.is_active
                updated = True
            if not staff.designation or staff.designation in ["Worker", "Bakery Worker"]:
                staff.designation = "Staff Driver"
                updated = True
            if updated:
                staff.save()
        return staff

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        try:
            self.sync_staff_profile()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("Failed to auto-sync driver staff profile: %s", e)


class DriverExpense(TimeStampedUUIDModel):
    """
    Operating expenses logged by drivers, managers, or owners (shop expenses, maintenance, fuel, food, etc.).
    Audit trail with driver isolation and manager/owner oversight.
    """
    class Category(models.TextChoices):
        SHOP_EXPENSE = "SHOP_EXPENSE", "Shop Expense"
        MAINTENANCE = "MAINTENANCE", "Shop & Vehicle Maintenance"
        RAW_MATERIAL = "RAW_MATERIAL", "Raw Materials / Packaging"
        PETROL_FUEL = "PETROL_FUEL", "Petrol / Fuel"
        PETROL = "PETROL", "Petrol"
        FOOD = "FOOD", "Food / Meals"
        PARKING = "PARKING", "Parking"
        TOLL = "TOLL", "Toll"
        UTILITY = "UTILITY", "Electricity / Rent / Utilities"
        SALARY_WAGES = "SALARY_WAGES", "Daily Wages / Allowance"
        VEHICLE_REPAIR = "VEHICLE_REPAIR", "Vehicle Expense"
        OTHER = "OTHER", "Other"

    driver = models.ForeignKey(
        Driver,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="expenses",
        help_text="Driver who incurred this expense (optional for shop or general expenses)"
    )
    category = models.CharField(
        max_length=50,
        choices=Category.choices,
        default=Category.SHOP_EXPENSE,
        db_index=True,
        help_text="Expense classification"
    )
    custom_category = models.CharField(
        max_length=100,
        blank=True,
        help_text="Custom category description if 'Other' selected"
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Expense amount in INR (always Decimal)"
    )
    date = models.DateField(
        default=timezone.localdate,
        db_index=True,
        help_text="Date on which expense occurred"
    )
    notes = models.TextField(blank=True, help_text="Remarks, vendor name, or invoice notes")
    receipt_reference = models.CharField(max_length=100, blank=True, help_text="Bill / receipt number")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="logged_driver_expenses"
    )

    class Meta:
        ordering = ["-date", "-created_at"]
        verbose_name = "Expense"
        verbose_name_plural = "Expenses"

    def __str__(self):
        category_name = self.custom_category if self.category == self.Category.OTHER and self.custom_category else self.get_category_display()
        driver_name = (self.driver.user.get_full_name() or self.driver.user.username) if self.driver and self.driver.user else "Shop/General"
        return f"{driver_name} - {category_name}: ₹{self.amount} ({self.date})"


class DriverShift(TimeStampedUUIDModel):
    """
    Driver daily shift tracking: Day Open (stock check & takeover of Kubbus & Romali ps)
    and Day Closing (reconciliation of stock, collections, and handovers).
    """
    driver = models.ForeignKey(
        Driver,
        on_delete=models.CASCADE,
        related_name="shifts",
        help_text="Driver running this shift"
    )
    date = models.DateField(
        default=timezone.localdate,
        db_index=True,
        help_text="Shift date"
    )
    # Opening
    is_opened = models.BooleanField(default=False)
    opened_at = models.DateTimeField(null=True, blank=True)
    kubbus_loaded = models.IntegerField(default=0, help_text="Total Kubbus pieces (ps) taken at start")
    romali_loaded = models.IntegerField(default=0, help_text="Total Romali pieces (ps) taken at start")
    opening_notes = models.TextField(blank=True)

    # Closing
    is_closed = models.BooleanField(default=False)
    closed_at = models.DateTimeField(null=True, blank=True)
    kubbus_returned = models.IntegerField(default=0, help_text="Unsold Kubbus pieces returned")
    romali_returned = models.IntegerField(default=0, help_text="Unsold Romali pieces returned")
    cash_collected = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    upi_collected = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    expenses_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    net_cash_handover = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    closing_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        unique_together = [("driver", "date")]
        verbose_name = "Driver Shift"
        verbose_name_plural = "Driver Shifts"

    def __str__(self):
        status = "Closed" if self.is_closed else ("Opened" if self.is_opened else "Pending")
        return f"{self.driver.driver_name} Shift ({self.date}): {status}"

