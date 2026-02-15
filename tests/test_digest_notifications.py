from datetime import date, datetime, time, timezone
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_app
from app.database.queries import ensure_notification_preference, ensure_user
from app.database.table_declarations import (
    NotificationDelivery,
    QSLDigestBatch,
    WebPushSubscription,
)
from app.services.digest_notifications import dispatch_digest_notifications_for_batch


class DigestNotificationTests(unittest.TestCase):
    def setUp(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self._temp_dir.name) / "test_digest_notify.db"
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
            },
            clear=False,
        )
        self._env.start()
        self.app = create_app()
        self.app.config.update(TESTING=True, DIGEST_BASE_URL="https://mobilelotw.org")

    def tearDown(self):
        self._env.stop()
        self._temp_dir.cleanup()

    def _seed_user_and_batch(self, *, add_subscription: bool) -> int:
        with self.app.config.get("SESSION_MAKER").begin() as session_:
            user = ensure_user(op="k1abc", session=session_)
            user.subscription_status = "active"
            user.lotw_auth_state = "ok"
            user.lotw_cookies_b = b"encrypted-cookie-data"
            user.email = "k1abc@example.com"
            user.timezone = "UTC"
            session_.add(user)
            session_.flush()

            preference = ensure_notification_preference(user=user, session=session_)
            preference.qsl_digest_enabled = True
            preference.fallback_to_email = True
            preference.qsl_digest_time_local = time(8, 0)

            if add_subscription:
                session_.add(
                    WebPushSubscription(
                        user_id=user.id,
                        endpoint="https://example.push/endpoint",
                        p256dh_key="abc",
                        auth_key="def",
                        status="active",
                    )
                )

            batch = QSLDigestBatch(
                user_id=user.id,
                digest_date=date(2026, 2, 14),
                window_start_utc=datetime(2026, 2, 13, 8, 0, tzinfo=timezone.utc),
                window_end_utc=datetime(2026, 2, 14, 8, 0, tzinfo=timezone.utc),
                qsl_count=2,
                payload_json={"qso_ids": [1, 2], "items": []},
            )
            session_.add(batch)
            session_.flush()
            return batch.id

    def test_push_success_skips_email(self):
        with self.app.app_context():
            batch_id = self._seed_user_and_batch(add_subscription=True)

            result = dispatch_digest_notifications_for_batch(
                batch_id=batch_id,
                push_sender=lambda *_args, **_kwargs: None,
                email_sender=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    RuntimeError("email should not be called")
                ),
            )

            self.assertEqual(result["push_status"], "sent")
            self.assertEqual(result["email_status"], "skipped")

            with self.app.config.get("SESSION_MAKER").begin() as session_:
                deliveries = session_.query(NotificationDelivery).all()
                statuses = {(d.channel, d.status) for d in deliveries}
                self.assertIn(("web_push", "sent"), statuses)
                self.assertIn(("email", "skipped"), statuses)

    def test_no_subscription_uses_email_fallback(self):
        with self.app.app_context():
            batch_id = self._seed_user_and_batch(add_subscription=False)
            result = dispatch_digest_notifications_for_batch(
                batch_id=batch_id,
                email_sender=lambda _message: "msg-1",
            )

            self.assertEqual(result["push_status"], "skipped")
            self.assertEqual(result["email_status"], "sent")

            with self.app.config.get("SESSION_MAKER").begin() as session_:
                deliveries = session_.query(NotificationDelivery).all()
                statuses = {(d.channel, d.status) for d in deliveries}
                self.assertIn(("web_push", "skipped"), statuses)
                self.assertIn(("email", "sent"), statuses)

    def test_push_failure_falls_back_to_email(self):
        with self.app.app_context():
            batch_id = self._seed_user_and_batch(add_subscription=True)
            result = dispatch_digest_notifications_for_batch(
                batch_id=batch_id,
                push_sender=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    RuntimeError("push down")
                ),
                email_sender=lambda _message: "msg-2",
            )

            self.assertEqual(result["push_status"], "failed")
            self.assertEqual(result["email_status"], "sent")

            with self.app.config.get("SESSION_MAKER").begin() as session_:
                deliveries = session_.query(NotificationDelivery).all()
                statuses = {(d.channel, d.status) for d in deliveries}
                self.assertIn(("web_push", "failed"), statuses)
                self.assertIn(("email", "sent"), statuses)
                push_subscription = session_.query(WebPushSubscription).first()
                self.assertEqual(push_subscription.failure_count, 1)

    def test_digest_notifications_disabled_skips_all_channels(self):
        with self.app.app_context():
            self.app.config["DIGEST_NOTIFICATIONS_ENABLED"] = False
            batch_id = self._seed_user_and_batch(add_subscription=True)
            result = dispatch_digest_notifications_for_batch(
                batch_id=batch_id,
                push_sender=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    RuntimeError("push should not run")
                ),
                email_sender=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    RuntimeError("email should not run")
                ),
            )
            self.assertEqual(result["push_status"], "skipped")
            self.assertEqual(result["email_status"], "skipped")

    def test_web_push_disabled_uses_email_fallback(self):
        with self.app.app_context():
            self.app.config["WEB_PUSH_ENABLED"] = False
            batch_id = self._seed_user_and_batch(add_subscription=True)
            result = dispatch_digest_notifications_for_batch(
                batch_id=batch_id,
                email_sender=lambda _message: "msg-disabled-push",
            )
            self.assertEqual(result["push_status"], "skipped")
            self.assertEqual(result["email_status"], "sent")


if __name__ == "__main__":
    unittest.main()
