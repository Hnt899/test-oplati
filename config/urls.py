"""Root URL configuration.

Static files in production: `django.conf.urls.static.static()` only adds routes when
``DEBUG`` is True, so it does *not* help on Render with ``DEBUG=False``. This project
uses **WhiteNoise** (see ``config.settings``) to serve ``STATIC_ROOT`` after
``collectstatic``.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.products.urls")),
]
