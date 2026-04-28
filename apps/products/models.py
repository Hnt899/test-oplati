"""Domain models for catalog and orders."""

from __future__ import annotations

import logging
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

logger = logging.getLogger(__name__)


class Currency(models.TextChoices):
    USD = "USD", "USD"
    RUB = "RUB", "RUB"


class Item(models.Model):
    """Sellable product; price is in smallest currency unit (cents/kopecks)."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.PositiveIntegerField(help_text="Amount in smallest currency unit")
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.RUB)

    class Meta:
        ordering = ["pk"]

    def __str__(self) -> str:
        return f"{self.name} ({self.currency})"


class DiscountType(models.TextChoices):
    PERCENT = "percent", "Percent"
    FIXED = "fixed", "Fixed amount (smallest currency unit)"


class Discount(models.Model):
    """Order-level discount; optional Stripe coupon id after sync."""

    name = models.CharField(max_length=255)
    discount_type = models.CharField(max_length=16, choices=DiscountType.choices)
    value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Percent (0–100) or fixed amount in smallest currency unit",
    )
    stripe_coupon_id = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["pk"]

    def __str__(self) -> str:
        return self.name


class Tax(models.Model):
    """Tax definition (exclusive); optional Stripe TaxRate id after sync."""

    name = models.CharField(max_length=255)
    rate_percent = models.DecimalField(max_digits=6, decimal_places=2)
    stripe_tax_rate_id = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["pk"]
        verbose_name_plural = "Taxes"

    def __str__(self) -> str:
        return f"{self.name} ({self.rate_percent}%)"


class Order(models.Model):
    """Cart/order composed of items with optional discount and tax."""

    items = models.ManyToManyField(Item, through="OrderItem", related_name="orders")
    discount = models.ForeignKey(
        Discount,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="orders",
    )
    tax = models.ForeignKey(
        Tax,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="orders",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def clean(self) -> None:
        currencies = self._item_currencies()
        if len(currencies) > 1:
            raise ValidationError(
                {"items": "All items in an order must use the same currency."},
            )

    def _item_currencies(self) -> set[str]:
        return set(
            self.order_items.values_list("item__currency", flat=True).distinct(),
        )

    def total_price(self) -> int:
        """Grand total in smallest currency unit (after discount, inclusive of tax)."""
        subtotal = self.subtotal_amount()
        after_discount = self._apply_discount(subtotal)
        tax_amt = self._tax_amount(after_discount)
        return after_discount + tax_amt

    def subtotal_amount(self) -> int:
        total = 0
        for oi in self.order_items.select_related("item").all():
            total += oi.item.price * oi.quantity
        return total

    def _apply_discount(self, subtotal: int) -> int:
        if not self.discount_id:
            return subtotal
        d = self.discount
        if d.discount_type == DiscountType.PERCENT:
            pct = Decimal(str(d.value))
            # integer-safe: subtotal * (100 - pct) / 100
            portion = Decimal(subtotal) * (Decimal(100) - pct) / Decimal(100)
            return int(portion.quantize(Decimal("1")))
        fixed = int(Decimal(str(d.value)))
        return max(0, subtotal - fixed)

    def _tax_amount(self, taxable_base: int) -> int:
        if not self.tax_id:
            return 0
        rate = Decimal(str(self.tax.rate_percent))
        return int((Decimal(taxable_base) * rate / Decimal(100)).quantize(Decimal("1")))

    def assert_single_currency(self) -> str:
        """Return currency code or raise ValidationError."""
        currencies = self._item_currencies()
        if not currencies:
            raise ValidationError("Order has no line items.")
        if len(currencies) > 1:
            raise ValidationError("Mixed currencies in one order are not allowed.")
        return next(iter(currencies))

    def __str__(self) -> str:
        return f"Order #{self.pk}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="order_items")
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="order_entries")
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = [("order", "item")]

    def __str__(self) -> str:
        return f"{self.quantity}× {self.item.name}"
