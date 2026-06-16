from django.contrib import admin

from .models import Experiment, ExperimentResponse


class ExperimentResponseInline(admin.TabularInline):
    model = ExperimentResponse
    extra = 0


@admin.register(Experiment)
class ExperimentAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "created_at")
    search_fields = ("title", "research_question")
    list_filter = ("status",)
    inlines = [ExperimentResponseInline]


@admin.register(ExperimentResponse)
class ExperimentResponseAdmin(admin.ModelAdmin):
    list_display = (
        "participant_code",
        "experiment",
        "assigned_condition",
        "confidence_score",
        "response_time_seconds",
        "created_at",
    )
    search_fields = ("participant_code", "decision", "notes")
    list_filter = ("assigned_condition",)
