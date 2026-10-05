import uuid
from decimal import Decimal
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from apps.common.models import TimeStampedUUIDModel

class User(AbstractUser):
    """
    Custom user model for Zamzam Foods.
    Supports 3 distinct business roles: OWNER, MANAGER, DRIVER.
    """
    class Role(models.TextChoices):
        OWNER = "OWNER", "Owner"
        MANAGER = "MANAGER", "Manager"
        DRIVER = "DRIVER", "Staff Driver"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.DRIVER,
        db_index=True,
        help_text="Designated role within the company"
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        help_text="Contact telephone/mobile number"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date_joined"]
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        full = self.get_full_name()
        return f"{full} ({self.role})" if full else f"{self.username} ({self.role})"

    @property
    def is_owner(self):
        return self.role == self.Role.OWNER or self.is_superuser

    @property
    def is_manager(self):
        return self.role == self.Role.MANAGER

    @property
    def is_driver(self):
        return self.role == self.Role.DRIVER


class DeviceSession(models.Model):
    """
    Tracks one active refresh-token per device for a User.
    Enables:
     - Per-device revocation (log out one device without affecting others)
     - Persistent login duration independent of JWT refresh-token lifetime
     - Multi-device support for Driver and Manager accounts
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="device_sessions",
    )
    # SHA-256 hex digest of the raw refresh token (never store plaintext tokens)
    refresh_token_hash = models.CharField(max_length=64, db_index=True)
    device_name = models.CharField(max_length=200, blank=True, default="")
    user_agent = models.TextField(blank=True, default="")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # Persistent session expiry — controls how long this device stays logged in
    expires_at = models.DateTimeField()
    last_used_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-last_used_at"]
        verbose_name = "Device Session"
        verbose_name_plural = "Device Sessions"

    def __str__(self):
        return f"{self.user.username} — {self.device_name or 'Unknown device'} (expires {self.expires_at:%Y-%m-%d})"

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def is_valid(self):
        return self.is_active and not self.is_expired


class StaffMember(TimeStampedUUIDModel):
    """
    Staff Profile for bakery workers, cleaners, drivers, managers, and helpers.
    Supports both:
    1) Staff with system login accounts (linked User profile).
    2) Workers without accounts / no software role ("no acounter no role profile").
    """
    class RoleType(models.TextChoices):
        STAFF = "STAFF", "Staff (Driver / Operations)"
        MEMBER = "MEMBER", "Share Member (Business Owner / Partner)"

    class WageType(models.TextChoices):
        DEFAULT_SLAB = "DEFAULT_SLAB", "Automatic Tenure Slabs (₹400/₹500/₹600/₹700/₹800)"
        CUSTOM = "CUSTOM", "Custom Daily Amount"

    role_type = models.CharField(
        max_length=20,
        choices=RoleType.choices,
        default=RoleType.MEMBER,
        db_index=True,
        help_text="Role classification: STAFF (Driver / Management / Operations) or MEMBER (Business Owner / Share Member)"
    )
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="staff_member_profile",
        help_text="Optional linked login user (if staff has login access)"
    )
    full_name = models.CharField(max_length=150, help_text="Full Name of staff member")
    phone_number = models.CharField(max_length=20, blank=True, help_text="Contact telephone/mobile number")
    designation = models.CharField(
        max_length=100,
        default="Share Member",
        help_text="Role/Designation e.g. Share Member, Business Partner, Staff Driver, Sales / Counter"
    )
    joined_date = models.DateField(
        default=timezone.localdate,
        help_text="Date when staff member joined Zamzam Foods"
    )
    wage_type = models.CharField(
        max_length=20,
        choices=WageType.choices,
        default=WageType.DEFAULT_SLAB,
        help_text="Default slab calculation or custom fixed wage"
    )
    custom_daily_wage = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        default=None,
        help_text="Custom daily wage if WageType is CUSTOM"
    )
    proof_document = models.FileField(
        upload_to="staff_proofs/",
        null=True,
        blank=True,
        help_text="Identity document / photo / PDF (Aadhaar, ID proof)"
    )
    is_active = models.BooleanField(default=True, help_text="Active employment status")
    notes = models.TextField(blank=True, help_text="Address, remarks, emergency contact")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_staff_profiles"
    )

    class Meta:
        ordering = ["full_name", "-created_at"]
        verbose_name = "Staff Member"
        verbose_name_plural = "Staff Members"

    def __str__(self):
        acc = f" (User: {self.user.username})" if self.user else " (No Login Account)"
        return f"{self.full_name} [{self.role_type}] - {self.designation}{acc}"

    @property
    def has_login_account(self) -> bool:
        return self.user is not None

    def get_daily_wage_for_date(self, target_date=None) -> Decimal:
        """
        Calculates daily wage based on joined_date:
        - First 2 months (< 60 days): ₹400
        - 2 to 6 months (60 to 180 days): ₹500
        - 6 to 12 months (180 to 365 days): ₹600
        - 1 to 2 years (365 to 730 days): ₹700
        - 2 years & beyond (730+ days): ₹800
        - Or custom_daily_wage if wage_type is CUSTOM
        """
        if self.wage_type == self.WageType.CUSTOM and self.custom_daily_wage is not None:
            return self.custom_daily_wage

        ref_date = target_date or timezone.localdate()
        if not self.joined_date:
            return Decimal("400.00")

        days = (ref_date - self.joined_date).days
        if days < 60:
            return Decimal("400.00")
        elif days < 180:
            return Decimal("500.00")
        elif days < 365:
            return Decimal("600.00")
        elif days < 730:
            return Decimal("700.00")
        else:
            return Decimal("800.00")

    @property
    def current_daily_wage(self) -> Decimal:
        return self.get_daily_wage_for_date()

    @property
    def tenure_days(self) -> int:
        if not self.joined_date:
            return 0
        return max(0, (timezone.localdate() - self.joined_date).days)

    @property
    def tenure_slab_label(self) -> str:
        if self.role_type == self.RoleType.MEMBER:
            if self.custom_daily_wage is not None:
                return f"Member Rate: ₹{self.custom_daily_wage}/day"
            return "Member Rate"
        if self.wage_type == self.WageType.CUSTOM and self.custom_daily_wage is not None:
            return f"Custom: ₹{self.custom_daily_wage}/day"
        days = self.tenure_days
        if days < 60:
            return f"< 2 Months ({days}d) — ₹400/day"
        elif days < 180:
            return f"2 to 6 Months ({days}d) — ₹500/day"
        elif days < 365:
            return f"6 to 12 Months ({days}d) — ₹600/day"
        elif days < 730:
            return f"1 to 2 Years ({days}d) — ₹700/day"
        else:
            return f"2+ Years ({days}d) — ₹800/day"

    def save(self, *args, **kwargs):
        if self.role_type == self.RoleType.MEMBER:
            self.wage_type = self.WageType.CUSTOM
        super().save(*args, **kwargs)


class StaffAttendance(TimeStampedUUIDModel):
    """
    Daily attendance record for a staff member.
    Status:
    - FULL: Full Day (100% daily wage)
    - HALF: Half Day (50% daily wage) - Members only
    - LEAVE: Leave / Absent (₹0 wage)
    """
    class Status(models.TextChoices):
        FULL = "FULL", "Full Day"
        HALF = "HALF", "Half Day"
        LEAVE = "LEAVE", "Leave / Absent"

    staff = models.ForeignKey(
        StaffMember,
        on_delete=models.CASCADE,
        related_name="attendances"
    )
    date = models.DateField(default=timezone.localdate, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.FULL,
        db_index=True
    )
    daily_wage = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Calculated wage for this attendance record"
    )
    notes = models.CharField(max_length=255, blank=True)
    marked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="marked_staff_attendances"
    )

    class Meta:
        ordering = ["-date", "staff__full_name"]
        unique_together = [("staff", "date")]
        verbose_name = "Staff Attendance"
        verbose_name_plural = "Staff Attendances"

    def __str__(self):
        return f"{self.staff.full_name} - {self.date}: {self.get_status_display()} (₹{self.daily_wage})"

    def save(self, *args, **kwargs):
        # Auto-calculate daily wage according to attendance status and staff joined_date slab
        base_rate = self.staff.get_daily_wage_for_date(self.date)
        # Staff role only has Full Day (Present) or Leave
        if self.staff.role_type == StaffMember.RoleType.STAFF and self.status == self.Status.HALF:
            self.status = self.Status.FULL

        if self.status == self.Status.FULL:
            self.daily_wage = base_rate
        elif self.status == self.Status.HALF:
            self.daily_wage = (base_rate / Decimal("2.00")).quantize(Decimal("0.01"))
        else:
            self.daily_wage = Decimal("0.00")
        super().save(*args, **kwargs)


class StaffPayout(TimeStampedUUIDModel):
    """
    Payouts / cash advances given to a staff member.
    Maintains a clear ledger of wages earned vs cash given.
    """
    class PayoutType(models.TextChoices):
        SALARY = "SALARY", "Salary / Wage Payout"
        ADVANCE = "ADVANCE", "Cash Advance"
        BONUS = "BONUS", "Bonus / Incentive"
        OTHER = "OTHER", "Other"

    class PaymentMethod(models.TextChoices):
        CASH = "CASH", "Cash"
        GPAY_UPI = "GPAY_UPI", "GPay / UPI"

    staff = models.ForeignKey(
        StaffMember,
        on_delete=models.CASCADE,
        related_name="payouts"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Amount paid in INR"
    )
    payout_type = models.CharField(
        max_length=30,
        choices=PayoutType.choices,
        default=PayoutType.SALARY
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH
    )
    date = models.DateField(default=timezone.localdate, db_index=True)
    reference = models.CharField(max_length=100, blank=True, help_text="Bill / receipt / UPI transaction ref")
    notes = models.TextField(blank=True, help_text="Remarks, e.g. weekly salary, advance for travel")
    paid_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="given_staff_payouts"
    )

    class Meta:
        ordering = ["-date", "-created_at"]
        verbose_name = "Staff Payout"
        verbose_name_plural = "Staff Payouts"

    def __str__(self):
        return f"{self.staff.full_name} - ₹{self.amount} ({self.get_payout_type_display()} on {self.date})"
