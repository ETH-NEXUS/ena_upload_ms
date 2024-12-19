"""
URL configuration for ena_upload_ms project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import re
from django.views.static import serve
from django.contrib import admin
from django.urls import path, re_path, include
from django.conf import settings
from drf_auto_endpoint.router import router

from rest_framework.authtoken import views as authtoken_views
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = []

# to support proxying to the ena service
prefix = settings.ENA_PROXY_PREFIX

urlpatterns = [
    path(f"{prefix}api-auth/", include("rest_framework.urls")),
    path(f"{prefix}admin/", admin.site.urls),
    path(f"{prefix}api/", include(router.urls)),
    path(f"{prefix}api/token/", authtoken_views.obtain_auth_token),
    path(f"{prefix}api/doc/", SpectacularAPIView.as_view(), name="schema"),
    path(
        f"{prefix}api/doc/swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        f"{prefix}api/doc/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]

if not settings.DEBUG:
    urlpatterns += [
        re_path(
            r"^%s(?P<path>.*)$" % re.escape(settings.STATIC_URL.lstrip("/")),
            serve,
            kwargs={"document_root": settings.STATIC_ROOT},
        ),
    ]
