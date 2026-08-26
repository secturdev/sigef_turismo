from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

urlpatterns = [
    path("", include("apps.landingpage.urls")),
    path("", include("apps.autenticacion.urls")),
    path("", include("apps.expediente.urls")),
    path("", include("apps.muestras.urls")),
    path("oidc/", include("mozilla_django_oidc.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
