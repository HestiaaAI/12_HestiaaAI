from django.core.validators import MinValueValidator
from django.db import models

from households.models import Membership, Workspace


class Product(models.Model):
    """
    Represents a standardized household product known to Hestia.

    It prevents differently worded names for the same product from
    becoming unrelated inventory records within one workspace.
    """

    product_id = models.AutoField(primary_key=True)

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="products",
    )

    canonical_name = models.CharField(max_length=150)
    category = models.CharField(max_length=60, blank=True)
    default_unit = models.CharField(max_length=30, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = [
            "workspace__name",
            "category",
            "canonical_name",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "canonical_name"],
                name="unique_product_name_per_workspace",
            )
        ]

    def __str__(self):
        return self.canonical_name


class SupplyItem(models.Model):
    """
    Represents a product whose quantity is tracked in a workspace.

    It stores the current and desired quantities so Hestia can identify
    products that need to be replenished.
    """

    supply_item_id = models.AutoField(primary_key=True)

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="supply_items",
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="supply_items",
    )

    is_tracked = models.BooleanField(default=True)

    target_level = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        validators=[MinValueValidator(0)],
    )

    current_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=0,
        validators=[MinValueValidator(0)],
    )

    quantity_unit = models.CharField(max_length=30)

    last_updated_by_membership = models.ForeignKey(
        Membership,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_supply_items",
    )

    last_updated_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = [
            "workspace__name",
            "product__canonical_name",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "product"],
                name="unique_tracked_product_per_workspace",
            )
        ]

    def __str__(self):
        return (
            f"{self.product.canonical_name}: "
            f"{self.current_quantity} {self.quantity_unit}"
        )


class ShoppingListEntry(models.Model):
    """
    Represents one item suggested or added to a workspace shopping list.

    It records the requested quantity, reason, creator, and current
    resolution state of the shopping request.
    """

    class EntryState(models.TextChoices):
        SUGGESTED = "SUGGESTED", "Suggested"
        ACCEPTED = "ACCEPTED", "Accepted"
        DISMISSED = "DISMISSED", "Dismissed"
        PURCHASED = "PURCHASED", "Purchased"
        REMOVED = "REMOVED", "Removed"

    shopping_list_entry_id = models.AutoField(primary_key=True)

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="shopping_list_entries",
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shopping_list_entries",
    )

    created_by_membership = models.ForeignKey(
        Membership,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_shopping_list_entries",
    )

    item_name = models.CharField(max_length=150)

    suggested_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=1,
        validators=[MinValueValidator(0)],
    )

    unit = models.CharField(max_length=30, blank=True)
    reason = models.CharField(max_length=255, blank=True)

    state = models.CharField(
        max_length=30,
        choices=EntryState.choices,
        default=EntryState.SUGGESTED,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = [
            "-created_at",
            "item_name",
        ]

    def __str__(self):
        return f"{self.item_name} - {self.get_state_display()}"