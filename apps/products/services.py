"""Stripe integration: key selection, Checkout Sessions, Payment Intents."""

from __future__ import annotations

import logging
from typing import Any

import stripe
from django.conf import settings

from apps.products.models import Currency, DiscountType, Item, Order

logger = logging.getLogger(__name__)


def _mask_secret_suffix(secret: str) -> str:
    """Last 8 chars of secret key for logs (never log full keys)."""
    if not secret:
        return "(empty)"
    return f"...{secret[-8:]}" if len(secret) > 8 else "***"


def _stripe_currency_code(currency: str) -> str:
    """Stripe expects lowercase ISO 4217 code (usd, rub)."""
    return currency.strip().upper()[:3].lower()


def get_secret_key_for_currency(currency: str) -> str:
    cur = currency.upper()
    if cur == Currency.USD:
        key = settings.STRIPE_SECRET_KEY_USD
        if not key:
            raise RuntimeError("STRIPE_SECRET_KEY_USD is not configured")
        return key
    key = settings.STRIPE_SECRET_KEY
    if not key:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured")
    return key


def get_publishable_key_for_currency(currency: str) -> str:
    cur = currency.upper()
    if cur == Currency.USD:
        pk = settings.STRIPE_PUBLISHABLE_KEY_USD
        if not pk:
            raise RuntimeError("STRIPE_PUBLISHABLE_KEY_USD is not configured")
        return pk
    pk = settings.STRIPE_PUBLISHABLE_KEY
    if not pk:
        raise RuntimeError("STRIPE_PUBLISHABLE_KEY is not configured")
    return pk


def get_publishable_key(currency: str) -> str:
    """Alias for views/templates expecting `get_publishable_key(currency)`."""
    return get_publishable_key_for_currency(currency)


def _stripe_request_options(currency: str) -> dict[str, Any]:
    return {"api_key": get_secret_key_for_currency(currency)}


def ensure_stripe_coupon(discount: Any, currency: str) -> str | None:
    """Return Stripe coupon id for Checkout Session discounts[]."""
    if discount.stripe_coupon_id:
        return discount.stripe_coupon_id
    opts = _stripe_request_options(currency)
    if discount.discount_type == DiscountType.PERCENT:
        coupon = stripe.Coupon.create(
            percent_off=float(discount.value),
            duration="once",
            name=discount.name[:40],
            **opts,
        )
    else:
        coupon = stripe.Coupon.create(
            amount_off=int(discount.value),
            currency=_stripe_currency_code(currency),
            duration="once",
            name=discount.name[:40],
            **opts,
        )
    discount.stripe_coupon_id = coupon.id
    discount.save(update_fields=["stripe_coupon_id"])
    logger.info("Created Stripe coupon %s for discount pk=%s", coupon.id, discount.pk)
    return coupon.id


def ensure_stripe_tax_rate(tax: Any, currency: str) -> str | None:
    if tax.stripe_tax_rate_id:
        return tax.stripe_tax_rate_id
    opts = _stripe_request_options(currency)
    tr = stripe.TaxRate.create(
        display_name=tax.name[:40],
        percentage=float(tax.rate_percent),
        inclusive=False,
        **opts,
    )
    tax.stripe_tax_rate_id = tr.id
    tax.save(update_fields=["stripe_tax_rate_id"])
    logger.info("Created Stripe TaxRate %s for tax pk=%s", tr.id, tax.pk)
    return tr.id


def build_success_cancel_urls() -> tuple[str, str]:
    """Absolute success/cancel URLs from ``settings.SITE_URL`` (Render / production safe)."""
    base = settings.SITE_URL.rstrip("/")
    success = f"{base}/checkout/success/"
    cancel = f"{base}/checkout/cancel/"
    logger.debug(
        "Stripe checkout redirects: SITE_URL=%s success_url=%s cancel_url=%s",
        settings.SITE_URL,
        success,
        cancel,
    )
    return success, cancel


def create_checkout_session_for_item(item: Item) -> stripe.checkout.Session:
    success_url, cancel_url = build_success_cancel_urls()
    opts = _stripe_request_options(item.currency)
    cur_code = _stripe_currency_code(item.currency)
    secret = opts.get("api_key", "")
    logger.info(
        "Checkout Session item_pk=%s stripe_cur=%s model_cur=%s key_suffix=%s",
        item.pk,
        cur_code,
        item.currency,
        _mask_secret_suffix(secret),
    )
    desc = (item.description or "")[:500]
    if cur_code == "usd" and item.price < 50:
        logger.warning(
            "Stripe USD Checkout usually requires at least 50 (cents); unit_amount=%s item_pk=%s",
            item.price,
            item.pk,
        )
    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[
                {
                    "price_data": {
                        "currency": cur_code,
                        "product_data": {"name": item.name, "description": desc},
                        "unit_amount": item.price,
                    },
                    "quantity": 1,
                }
            ],
            success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url,
            **opts,
        )
    except stripe.error.StripeError as exc:
        logger.exception(
            "Stripe Checkout Session failed item_pk=%s cur=%s code=%s status=%s msg=%s",
            item.pk,
            item.currency,
            cur_code,
            getattr(exc, "http_status", None),
            getattr(exc, "user_message", None) or str(exc),
        )
        raise
    logger.info(
        "Checkout Session created session_id=%s item_pk=%s currency=%s",
        session.id,
        item.pk,
        cur_code,
    )
    return session


def create_checkout_session_for_order(order: Order) -> stripe.checkout.Session:
    currency = order.assert_single_currency()
    cur_code = _stripe_currency_code(currency)
    success_url, cancel_url = build_success_cancel_urls()
    opts = _stripe_request_options(currency)
    logger.info(
        "Creating Checkout Session for order_pk=%s stripe_currency=%s secret_suffix=%s",
        order.pk,
        cur_code,
        _mask_secret_suffix(opts.get("api_key", "")),
    )

    tax_rate_id: str | None = None
    if order.tax_id:
        tax_rate_id = ensure_stripe_tax_rate(order.tax, currency)

    line_items: list[dict[str, Any]] = []
    for oi in order.order_items.select_related("item").all():
        desc = (oi.item.description or "")[:500]
        li: dict[str, Any] = {
            "price_data": {
                "currency": _stripe_currency_code(oi.item.currency),
                "product_data": {
                    "name": oi.item.name,
                    "description": desc,
                },
                "unit_amount": oi.item.price,
            },
            "quantity": oi.quantity,
        }
        if tax_rate_id:
            li["tax_rates"] = [tax_rate_id]
        line_items.append(li)

    payload: dict[str, Any] = {
        "mode": "payment",
        "line_items": line_items,
        "success_url": success_url + "?session_id={CHECKOUT_SESSION_ID}",
        "cancel_url": cancel_url,
        **opts,
    }

    if order.discount_id:
        cid = ensure_stripe_coupon(order.discount, currency)
        if cid:
            payload["discounts"] = [{"coupon": cid}]

    try:
        session = stripe.checkout.Session.create(**payload)
    except stripe.error.StripeError as exc:
        logger.exception(
            "Stripe Checkout Session order failed pk=%s cur=%s status=%s msg=%s",
            order.pk,
            currency,
            getattr(exc, "http_status", None),
            getattr(exc, "user_message", None) or str(exc),
        )
        raise
    logger.info("Checkout Session created order_pk=%s session_id=%s", order.pk, session.id)
    return session


def create_payment_intent_for_item(item: Item) -> stripe.PaymentIntent:
    opts = _stripe_request_options(item.currency)
    cur_code = _stripe_currency_code(item.currency)
    logger.info(
        "Creating PaymentIntent item_pk=%s currency=%s secret_suffix=%s",
        item.pk,
        cur_code,
        _mask_secret_suffix(opts.get("api_key", "")),
    )
    try:
        intent = stripe.PaymentIntent.create(
            amount=item.price,
            currency=cur_code,
            metadata={"item_id": str(item.pk)},
            automatic_payment_methods={"enabled": True},
            **opts,
        )
    except stripe.error.StripeError as exc:
        logger.exception(
            "Stripe PaymentIntent failed item_pk=%s currency=%s http_status=%s stripe_msg=%s",
            item.pk,
            cur_code,
            getattr(exc, "http_status", None),
            getattr(exc, "user_message", None) or str(exc),
        )
        raise
    intent_id = getattr(intent, "id", "")
    logger.info("PaymentIntent created item_pk=%s intent=%s", item.pk, intent_id)
    return intent
