# src/assessments/admin.py
from django.contrib import admin

from .models import Assessment


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at", "writing_submitted_at")
