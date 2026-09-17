from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from households.models import Membership, Workspace


class SourceDocument(models.Model):
    """
    Represents an original document received by Hestia.

    It preserves receipts, emails, notices, photos, and other source
    material so extracted information remains traceable to its source.
    """

    class DocumentType(models.TextChoices):
        RECEIPT = "RECEIPT", "Receipt"
        EMAIL = "EMAIL", "Email"
        NOTICE = "NOTICE", "Notice"
        PHOTO = "PHOTO", "Photo"
        PDF = "PDF", "PDF"
        PURCHASE_CONFIRMATION = (
            "PURCHASE_CONFIRMATION",
            "Purchase confirmation",
        )
        OTHER = "OTHER", "Other"

    class ProcessingState(models.TextChoices):
        RECEIVED = "RECEIVED", "Received"
        PROCESSING = "PROCESSING", "Processing"
        NEEDS_REVIEW = "NEEDS_REVIEW", "Needs review"
        CONFIRMED = "CONFIRMED", "Confirmed"
        FAILED = "FAILED", "Failed"

    source_document_id = models.AutoField(primary_key=True)

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="source_documents",
    )

    uploaded_by_membership = models.ForeignKey(
        Membership,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_documents",
    )

    document_type = models.CharField(
        max_length=40,
        choices=DocumentType.choices,
        default=DocumentType.OTHER,
    )

    subject = models.CharField(
        max_length=255,
        blank=True,
    )
    sender = models.CharField(
        max_length=255,
        blank=True,
    )
    original_filename = models.CharField(
        max_length=255,
        blank=True,
    )
    raw_text = models.TextField(blank=True)
    content_hash = models.CharField(max_length=128)

    received_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    ingested_at = models.DateTimeField(auto_now_add=True)

    processing_state = models.CharField(
        max_length=30,
        choices=ProcessingState.choices,
        default=ProcessingState.RECEIVED,
    )

    class Meta:
        ordering = ["-received_at", "subject"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "content_hash"],
                name="unique_document_hash_per_workspace",
            )
        ]

    def __str__(self):
        label = self.subject or self.original_filename or "Untitled document"
        return f"{label} ({self.get_document_type_display()})"


class ExtractedField(models.Model):
    """
    Represents one structured value extracted from a source document.

    It stores an AI-extracted value, its confidence score, and any
    subsequent human confirmation while preserving the original value.
    """

    class FieldState(models.TextChoices):
        SUGGESTED = "SUGGESTED", "Suggested"
        CONFIRMED = "CONFIRMED", "Confirmed"
        CORRECTED = "CORRECTED", "Corrected"
        REJECTED = "REJECTED", "Rejected"
        UNRESOLVED = "UNRESOLVED", "Unresolved"

    extracted_field_id = models.AutoField(primary_key=True)

    source_document = models.ForeignKey(
        SourceDocument,
        on_delete=models.CASCADE,
        related_name="extracted_fields",
    )

    field_path = models.CharField(max_length=150)
    raw_value = models.TextField(blank=True)
    extracted_value = models.TextField(blank=True)
    confirmed_value = models.TextField(blank=True)

    confidence = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1),
        ],
    )

    state = models.CharField(
        max_length=30,
        choices=FieldState.choices,
        default=FieldState.SUGGESTED,
    )

    confirmed_by_membership = models.ForeignKey(
        Membership,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="confirmed_extracted_fields",
    )

    confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["source_document", "field_path"]
        constraints = [
            models.UniqueConstraint(
                fields=["source_document", "field_path"],
                name="unique_field_path_per_document",
            )
        ]

    def __str__(self):
        return f"{self.field_path}: {self.extracted_value}"