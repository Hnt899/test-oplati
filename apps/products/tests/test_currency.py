"""Tests for Stripe multi-account key selection."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.test import Client


@pytest.mark.django_db
def test_rub_item_uses_rub_keys(rub_item: object, client: Client) -> None:
    fake = SimpleNamespace(id="cs_rub")
    with patch("stripe.checkout.Session.create", return_value=fake) as m:
        client.get(f"/buy/{rub_item.pk}/")
    kwargs = m.call_args.kwargs
    assert kwargs.get("api_key") == "sk_test_rub"


@pytest.mark.django_db
def test_usd_item_uses_usd_keys(usd_item: object, client: Client) -> None:
    fake = SimpleNamespace(id="cs_usd")
    with patch("stripe.checkout.Session.create", return_value=fake) as m:
        client.get(f"/buy/{usd_item.pk}/")
    kwargs = m.call_args.kwargs
    assert kwargs.get("api_key") == "sk_test_usd"
