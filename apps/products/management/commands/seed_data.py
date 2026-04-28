"""Populate DB with demo catalog, discount, and tax."""

from django.core.management.base import BaseCommand

from apps.products.models import Currency, Discount, DiscountType, Item, Tax


class Command(BaseCommand):
    help = "Creates demo items (RUB and EUR), a sample discount, and a sample tax."

    def handle(self, *args: object, **options: object) -> None:
        rub_items = [
            ("Demo Mug RUB", "Ceramic mug with logo.", 990_00, Currency.RUB),
            ("Sticker Pack RUB", "Vinyl stickers.", 450_00, Currency.RUB),
            ("T-Shirt RUB", "Soft cotton tee.", 2490_00, Currency.RUB),
        ]
        eur_items = [
            ("AI Credits EUR", "Starter credit bundle.", 999, Currency.EUR),
            ("API Pass EUR", "Monthly API access.", 2499, Currency.EUR),
        ]

        for name, desc, price, cur in rub_items + eur_items:
            Item.objects.update_or_create(
                name=name,
                defaults={"description": desc, "price": price, "currency": cur},
            )

        Discount.objects.update_or_create(
            name="Demo 10% off",
            defaults={
                "discount_type": DiscountType.PERCENT,
                "value": "10.00",
                "stripe_coupon_id": "",
            },
        )

        Tax.objects.update_or_create(
            name="Demo VAT",
            defaults={"rate_percent": "20.00", "stripe_tax_rate_id": ""},
        )

        self.stdout.write(self.style.SUCCESS("Seed data applied."))
