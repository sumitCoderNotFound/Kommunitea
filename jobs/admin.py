from django.contrib import admin
from .models import Job


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ["title", "company", "location", "job_type", "visa_sponsorship", "is_active", "created_at"]
    list_filter = ["job_type", "visa_sponsorship", "is_active"]
    search_fields = ["title", "company", "location"]
    list_editable = ["is_active"]
