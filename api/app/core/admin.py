from django.contrib import admin
from .models import Job, AnalysisJob


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    pass


@admin.register(AnalysisJob)
class AnalysisJobAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "job",
        "status",
        "created_at",
        "template",
        "data",
    )
    search_fields = ()

    list_filter = ("status",)
