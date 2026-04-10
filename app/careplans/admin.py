from django.contrib import admin
from .models import CarePlanJob


@admin.register(CarePlanJob)
class CarePlanJobAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "status", "created_at", "updated_at")
    list_filter = ("status", "created_at")
    readonly_fields = ("created_at", "updated_at")
