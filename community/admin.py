from django.contrib import admin
from .models import Member


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ["full_name", "city", "uk_status", "professional_field", "experience", "is_approved", "created_at"]
    list_filter = ["uk_status", "professional_field", "experience", "is_approved"]
    search_fields = ["full_name", "email", "city"]
    list_editable = ["is_approved"]
