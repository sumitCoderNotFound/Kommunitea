from django.contrib import admin
from .models import TeamMember


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ["name", "role", "city", "experience", "display_order", "is_active"]
    list_filter = ["role", "is_active"]
    search_fields = ["name", "skills", "city"]
    list_editable = ["display_order", "is_active"]
