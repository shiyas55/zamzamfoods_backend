import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

class User(AbstractUser):
    """
    Custom user model for Zamzam Foods.
    Supports 3 distinct business roles: OWNER, MANAGER, DRIVER.
    """
    class Role(models.TextChoices):
        OWNER = "OWNER", "Owner"
        MANAGER = "MANAGER", "Manager"
        DRIVER = "DRIVER", "Driver"

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
