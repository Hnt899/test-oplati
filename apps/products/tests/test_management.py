"""Management command tests."""

from __future__ import annotations

import pytest
from django.core.management import call_command

from apps.products.models import Item


@pytest.mark.django_db
def test_seed_data_command() -> None:
    call_command("seed_data")
    assert Item.objects.filter(currency="RUB").count() >= 3
    assert Item.objects.filter(currency="EUR").count() >= 2
