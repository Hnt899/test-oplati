"""Django admin registrations."""

from django.contrib import admin

from apps.products.models import Discount, Item, Order, OrderItem, Tax


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "currency", "pk")
    search_fields = ("name",)


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ("name", "discount_type", "value", "stripe_coupon_id")


@admin.register(Tax)
class TaxAdmin(admin.ModelAdmin):
    list_display = ("name", "rate_percent", "stripe_tax_rate_id")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("pk", "created_at", "discount", "tax")
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "item", "quantity")
