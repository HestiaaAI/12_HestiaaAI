from django.contrib import admin

from .models import Product, ShoppingListEntry, SupplyItem


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "product_id",
        "canonical_name",
        "category",
        "default_unit",
        "workspace",
    )
    search_fields = (
        "canonical_name",
        "category",
        "workspace__name",
    )
    list_filter = (
        "category",
        "workspace",
    )
    ordering = ("canonical_name",)
    list_select_related = ("workspace",)


@admin.register(SupplyItem)
class SupplyItemAdmin(admin.ModelAdmin):
    list_display = (
        "supply_item_id",
        "product",
        "workspace",
        "current_quantity",
        "target_level",
        "quantity_unit",
        "is_tracked",
        "last_updated_by_membership",
        "last_updated_at",
    )
    search_fields = (
        "product__canonical_name",
        "workspace__name",
        "last_updated_by_membership__display_name",
    )
    list_filter = (
        "is_tracked",
        "workspace",
        "product__category",
    )
    ordering = (
        "workspace",
        "product",
    )
    list_select_related = (
        "workspace",
        "product",
        "last_updated_by_membership",
    )


@admin.register(ShoppingListEntry)
class ShoppingListEntryAdmin(admin.ModelAdmin):
    list_display = (
        "shopping_list_entry_id",
        "item_name",
        "product",
        "suggested_quantity",
        "unit",
        "state",
        "workspace",
        "created_by_membership",
    )
    search_fields = (
        "item_name",
        "reason",
        "product__canonical_name",
        "workspace__name",
        "created_by_membership__display_name",
    )
    list_filter = (
        "state",
        "workspace",
    )
    ordering = ("-created_at",)
    list_select_related = (
        "workspace",
        "product",
        "created_by_membership",
    )
    date_hierarchy = "created_at"