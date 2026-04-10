from django.db import models
from app.models import Order


class CarePlanJob(models.Model):
    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
    ]

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="careplan_job")
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default=STATUS_PENDING)

    care_plan_text = models.TextField(blank=True, default="")
    error_message = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"CarePlanJob#{self.id} ({self.status})"
