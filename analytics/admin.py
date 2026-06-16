from django.contrib import admin

from .models import BusinessKPI, BusinessReport, ChatMessage, DatasetImport


@admin.register(DatasetImport)
class DatasetImportAdmin(admin.ModelAdmin):
    list_display = ("file_name", "status", "rows_loaded", "extracted_at", "processed_at")
    search_fields = ("file_name", "notes")
    list_filter = ("status",)


@admin.register(BusinessKPI)
class BusinessKPIAdmin(admin.ModelAdmin):
    list_display = ("name", "value", "category", "created_at")
    search_fields = ("name", "value", "category")
    list_filter = ("category",)


@admin.register(BusinessReport)
class BusinessReportAdmin(admin.ModelAdmin):
    list_display = ("title", "created_at")
    search_fields = ("title", "content")


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("question", "created_at")
    search_fields = ("question", "answer")
