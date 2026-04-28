"""URL routes for products app."""

from django.urls import path

from apps.products import views

urlpatterns = [
    path("", views.item_list, name="item-list"),
    path("item/<int:pk>/", views.item_page, name="item-detail"),
    path("buy/<int:pk>/", views.buy, name="buy"),
    path("buy-intent/<int:pk>/", views.buy_intent, name="buy-intent"),
    path("create-order/", views.create_order, name="create-order"),
    path("checkout/success/", views.checkout_success, name="checkout-success"),
    path("checkout/cancel/", views.checkout_cancel, name="checkout-cancel"),
]
