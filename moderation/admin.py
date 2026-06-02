from django.contrib import admin
from .models import Report, Block


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ["target_type", "target_id", "reason", "reporter", "status", "created_at"]
    list_filter = ["target_type", "reason", "status"]
    list_editable = ["status"]
    actions = ["mark_resolved", "mark_dismissed"]

    @admin.action(description="Mark selected reports resolved")
    def mark_resolved(self, request, queryset):
        queryset.update(status="resolved")

    @admin.action(description="Dismiss selected reports")
    def mark_dismissed(self, request, queryset):
        queryset.update(status="dismissed")


admin.site.register(Block)
