from django.db import models
from django.utils import timezone
from apps.common.models import TimeStampedUUIDModel
from apps.orders.models import Order
from apps.routes.models import Driver, Route

class Delivery(TimeStampedUUIDModel):
    """
    Delivery dispatch assignment for a driver on a specific route.
    """
    class Status(models.TextChoices):
        ASSIGNED = "ASSIGNED", "Assigned"
        IN_TRANSIT = "IN_TRANSIT", "In Transit"
        DELIVERED = "DELIVERED", "Delivered"
        NOT_DELIVERED = "NOT_DELIVERED", "Not Delivered"
        FAILED = "FAILED", "Failed"
        RETURNED = "RETURNED", "Returned"

    delivery_number = models.CharField(
        max_length=30,
        unique=True,
        db_index=True,
        help_text="Unique delivery dispatch code (e.g. DEL-20260926-0001)"
    )
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="delivery"
    )
    driver = models.ForeignKey(
        Driver,
        on_delete=models.PROTECT,
        related_name="deliveries",
        help_text="Assigned delivery driver"
    )
    route = models.ForeignKey(
        Route,
        on_delete=models.PROTECT,
        related_name="deliveries"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ASSIGNED,
        db_index=True
    )
    delivered_at = models.DateTimeField(null=True, blank=True)
    recipient_name = models.CharField(max_length=100, blank=True, help_text="Shop staff who acknowledged delivery")
    failed_reason = models.CharField(max_length=255, blank=True, help_text="Reason if shop was closed or refused")
    notes = models.TextField(blank=True, help_text="Delivery confirmation remarks")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Delivery Dispatch"
        verbose_name_plural = "Delivery Dispatches"

    def __str__(self):
        return f"{self.delivery_number} - {self.order.customer.name} ({self.status})"
