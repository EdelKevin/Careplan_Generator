from django.contrib import admin

from .models import Provider, Patient, Order


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "npi")
    search_fields = ("name", "npi")


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("id", "first_name", "last_name", "mrn", "primary_diagnosis")
    search_fields = ("first_name", "last_name", "mrn")
    list_filter = ("primary_diagnosis",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "patient", "provider", "medication_name", "created_at")
    search_fields = ("medication_name",)
    list_filter = ("created_at",)
