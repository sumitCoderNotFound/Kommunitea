from django.contrib import admin
from .models import Task, WeeklyGoal, Opportunity

admin.site.register(Task)
admin.site.register(WeeklyGoal)
admin.site.register(Opportunity)
