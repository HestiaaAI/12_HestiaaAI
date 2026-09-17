from django.contrib import admin

from .models import ExtractedField, SourceDocument


@admin.register(SourceDocument)
class SourceDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "source_document_id",
        "subject",
        "document_type",
        "workspace",
        "uploaded_by_membership",
        "processing_state",
        "received_at",
    )
    search_fields = (
        "subject",
        "sender",
        "original_filename",
        "raw_text",
        "workspace__name",
        "uploaded_by_membership__display_name",
    )
    list_filter = (
        "document_type",
        "processing_state",
        "workspace",
    )
    ordering = ("-received_at",)
    list_select_related = (
        "workspace",
        "uploaded_by_membership",
    )
    date_hierarchy = "received_at"


@admin.register(ExtractedField)
class ExtractedFieldAdmin(admin.ModelAdmin):
    list_display = (
        "extracted_field_id",
        "field_path",
        "source_document",
        "extracted_value",
        "confidence",
        "state",
        "confirmed_by_membership",
    )
    search_fields = (
        "field_path",
        "raw_value",
        "extracted_value",
        "confirmed_value",
        "source_document__subject",
    )
    list_filter = (
        "state",
        "source_document__document_type",
    )
    ordering = (
        "source_document",
        "field_path",
    )
    list_select_related = (
        "source_document",
        "confirmed_by_membership",
    )