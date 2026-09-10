from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from apps.autenticacion.middleware import OIDCCanonicalOriginMiddleware


class OIDCCanonicalOriginMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.get_response = lambda request: HttpResponse("ok")

    @override_settings(OIDC_CANONICAL_ORIGIN="http://localhost:8000")
    def test_redirects_oidc_request_from_alias_to_canonical_origin(self):
        middleware = OIDCCanonicalOriginMiddleware(self.get_response)
        request = self.factory.get(
            "/oidc/authenticate/?next=/dashboard/", HTTP_HOST="127.0.0.1:8000"
        )

        response = middleware(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            "http://localhost:8000/oidc/authenticate/?next=/dashboard/",
        )

    @override_settings(OIDC_CANONICAL_ORIGIN="http://localhost:8000")
    def test_allows_request_already_using_canonical_origin(self):
        middleware = OIDCCanonicalOriginMiddleware(self.get_response)
        request = self.factory.get(
            "/oidc/authenticate/", HTTP_HOST="localhost:8000"
        )

        response = middleware(request)

        self.assertEqual(response.status_code, 200)

    @override_settings(OIDC_CANONICAL_ORIGIN="http://localhost:8000")
    def test_does_not_redirect_non_oidc_request(self):
        middleware = OIDCCanonicalOriginMiddleware(self.get_response)
        request = self.factory.get("/inicio/", HTTP_HOST="127.0.0.1:8000")

        response = middleware(request)

        self.assertEqual(response.status_code, 200)

    @override_settings(OIDC_CANONICAL_ORIGIN="localhost:8000/oidc")
    def test_rejects_invalid_origin_setting(self):
        with self.assertRaises(ImproperlyConfigured):
            OIDCCanonicalOriginMiddleware(self.get_response)
