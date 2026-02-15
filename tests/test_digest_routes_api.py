from datetime import date, datetime, time, timezone
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_app
from app.database.queries import ensure_notification_preference, ensure_user, get_user
from app.database.table_declarations import QSLDigestBatch, QSOReport, WebPushSubscription


class DigestRoutesApiTests(unittest.TestCase):
    def setUp(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self._temp_dir.name) / "test_digest_routes.db"
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
                "WEB_PUSH_VAPID_PUBLIC_KEY": "test_public_key",
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
                user.subscription_status = "active"
                user.lotw_auth_state = "ok"
                user.lotw_cookies_b = b"encrypted-cookie-data"
                user.timezone = "UTC"
                user.email = "k1abc@example.com"
                session_.add(user)
                session_.flush()

                preference = ensure_notification_preference(user=user, session=session_)
                preference.qsl_digest_enabled = True
                preference.qsl_digest_time_local = time(8, 0)
                preference.fallback_to_email = True

                qso = QSOReport(
                    user_id=user.id,
                    call="W1AW",
                    app_lotw_qso_timestamp=datetime(
                        2026, 2, 14, 1, 0, tzinfo=timezone.utc
                    ),
                    app_lotw_rxqsl=datetime(2026, 2, 14, 7, 0, tzinfo=timezone.utc),
                )
                session_.add(qso)
                session_.flush()

                batch = QSLDigestBatch(
                    user_id=user.id,
                    digest_date=date(2026, 2, 14),
                    window_start_utc=datetime(
                        2026, 2, 13, 8, 0, tzinfo=timezone.utc
                    ),
                    window_end_utc=datetime(2026, 2, 14, 8, 0, tzinfo=timezone.utc),
                    qsl_count=1,
                    payload_json={"qso_ids": [qso.id], "items": []},
                )
                session_.add(batch)

        with self.client.session_transaction() as flask_session:
            flask_session["logged_in"] = True
            flask_session["op"] = "k1abc"

    def tearDown(self):
        self._env.stop()
        self._temp_dir.cleanup()

    def test_digest_page_renders_batch(self):
        response = self.client.get("/qsl/digest?date=2026-02-14")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("QSL Digest 2026-02-14", body)
        self.assertIn("W1AW", body)

    def test_notification_settings_post_updates_user_and_preference(self):
        response = self.client.post(
            "/notifications/settings",
            data={
                "qsl_digest_enabled": "on",
                "qsl_digest_time_local": "09:30",
                "timezone": "America/New_York",
                "locale": "en-US",
                "fallback_to_email": "on",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            with self.app.config.get("SESSION_MAKER").begin() as session_:
                user = get_user(op="k1abc", session=session_)
                preference = user.notification_preference
                self.assertEqual(user.timezone, "America/New_York")
                self.assertEqual(user.locale, "en-US")
                self.assertEqual(preference.qsl_digest_time_local.hour, 9)
                self.assertEqual(preference.qsl_digest_time_local.minute, 30)

    def test_web_push_subscribe_and_unsubscribe(self):
        subscribe_response = self.client.post(
            "/api/v1/notifications/web-push/subscribe",
            json={
                "endpoint": "https://example.push/sub-1",
                "keys": {"p256dh": "abc", "auth": "def"},
                "platform": "MacIntel",
            },
        )
        self.assertEqual(subscribe_response.status_code, 200)

        with self.app.app_context():
            with self.app.config.get("SESSION_MAKER").begin() as session_:
                subscription = session_.query(WebPushSubscription).first()
                self.assertIsNotNone(subscription)
                self.assertEqual(subscription.status, "active")

        unsubscribe_response = self.client.post(
            "/api/v1/notifications/web-push/unsubscribe",
            json={"endpoint": "https://example.push/sub-1"},
        )
        self.assertEqual(unsubscribe_response.status_code, 200)

        with self.app.app_context():
            with self.app.config.get("SESSION_MAKER").begin() as session_:
                subscription = session_.query(WebPushSubscription).first()
                self.assertIsNotNone(subscription)
                self.assertEqual(subscription.status, "unsubscribed")


if __name__ == "__main__":
    unittest.main()
