"""Migrate Item.currency USD → EUR and update choices."""

from django.db import migrations, models


def forwards_usd_to_eur(apps, schema_editor) -> None:
    Item = apps.get_model("products", "Item")
    Item.objects.filter(currency="USD").update(currency="EUR")


def backwards_eur_to_usd(apps, schema_editor) -> None:
    Item = apps.get_model("products", "Item")
    Item.objects.filter(currency="EUR").update(currency="USD")


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(forwards_usd_to_eur, backwards_eur_to_usd),
        migrations.AlterField(
            model_name="item",
            name="currency",
            field=models.CharField(
                choices=[("EUR", "EUR"), ("RUB", "RUB")],
                default="RUB",
                max_length=3,
            ),
        ),
    ]
