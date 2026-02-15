import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app import create_app
from app.database.queries import ensure_user


class _FakeStripe:
    api_key = None
    customer_kwargs = None
    checkout_kwargs = None

    class Customer:
        @staticmethod
        def create(**kwargs):
            _FakeStripe.customer_kwargs = kwargs
            return SimpleNamespace(id="cus_test_123")

    class checkout:
        class Session:
            @staticmethod
            def create(**kwargs):
                _FakeStripe.checkout_kwargs = kwargs
                return SimpleNamespace(url="https://stripe.test/checkout")


class BillingCheckoutPlanTests(unittest.TestCase):
    def setUp(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self._temp_dir.name) / "test_billing.db"
        self._env = patch.dict(
            os.environ,
            {
                "MOBILE_LOTW_SECRET_KEY": "test-secret-key",
                "MOBILE_LOTW_DB_KEY": "abcdefghijklmnop",
                "DB_URL": f"sqlite:///{db_path}",
                "API_KEY": "test-api-key",
                "DEPLOY_SCRIPT_PATH": "/tmp/deploy.sh",
                "SESSION_CACHE_EXPIRATION": "30",
                "MOBILE_LOTW_SECURE_COOKIES": "0",
                "STRIPE_SECRET_KEY": "sk_test_123",
                "STRIPE_WEBHOOK_SECRET": "whsec_test_123",
                "STRIPE_PRICE_ID_MONTHLY": "price_monthly_123",
                "STRIPE_PRICE_ID_ANNUAL": "price_annual_123",
            },
            clear=False,
        )
        self._env.start()
        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

        with self.app.app_context():
            with self.app.config.get("SESSION_MAKER").begin() as session_:
                user = ensure_user(op="k1abc", session=session_)
                user.has_imported = True
                user.lotw_cookies = {"lotw_session": "cookie-value"}
                user.email = "k1abc@example.com"
                session_.add(user)

        with self.client.session_transaction() as flask_session:
            flask_session["logged_in"] = True
            flask_session["op"] = "k1abc"

    def tearDown(self):
        self._env.stop()
        self._temp_dir.cleanup()

    @patch("app.blueprints.billing.overview._get_stripe", return_value=_FakeStripe)
    def test_checkout_defaults_to_monthly_plan(self, _mock_get_stripe):
        _FakeStripe.checkout_kwargs = None

        response = self.client.post(
            "/api/v1/billing/create-checkout-session",
            json={},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["checkout_url"], "https://stripe.test/checkout")
        self.assertIsNotNone(_FakeStripe.checkout_kwargs)
        self.assertEqual(
            _FakeStripe.checkout_kwargs["line_items"][0]["price"],
            "price_monthly_123",
        )

    @patch("app.blueprints.billing.overview._get_stripe", return_value=_FakeStripe)
    def test_checkout_supports_annual_plan(self, _mock_get_stripe):
        _FakeStripe.checkout_kwargs = None

        response = self.client.post(
            "/api/v1/billing/create-checkout-session",
            json={"plan": "annual"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["checkout_url"], "https://stripe.test/checkout")
        self.assertIsNotNone(_FakeStripe.checkout_kwargs)
        self.assertEqual(
            _FakeStripe.checkout_kwargs["line_items"][0]["price"],
            "price_annual_123",
        )

    @patch("app.blueprints.billing.overview._get_stripe", return_value=_FakeStripe)
    def test_checkout_rejects_unknown_plan(self, _mock_get_stripe):
        response = self.client.post(
            "/api/v1/billing/create-checkout-session",
            json={"plan": "weekly"},
        )

        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertEqual(payload["error"], "invalid_plan")


if __name__ == "__main__":
    unittest.main()
