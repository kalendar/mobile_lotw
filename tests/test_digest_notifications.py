from datetime import date, datetime, time, timedelta, timezone
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import select

from app import create_app
from app.database.queries import ensure_notification_preference, ensure_user
from app.database.table_declarations import (
    NotificationDelivery,
    QSLDigestBatch,
    WebPushSubscription,
)
from app.services.digest_notifications import (
    dispatch_digest_notifications_for_batch,
    dispatch_pending_digest_notifications,
)


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

    def _seed_user_and_batch(
        self,
        *,
        add_subscription: bool,
        digest_date: date = date(2026, 2, 14),
        qsl_count: int = 2,
    ) -> int:
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
                digest_date=digest_date,
                window_end_utc=datetime(
                    digest_date.year,
                    digest_date.month,
                    digest_date.day,
                    8,
                    0,
                    tzinfo=timezone.utc,
                ),
                window_start_utc=datetime(
                    digest_date.year,
                    digest_date.month,
                    digest_date.day,
                    8,
                    0,
                    tzinfo=timezone.utc,
                )
                - timedelta(days=1),
                qsl_count=qsl_count,
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
            captured_to = {"value": None}

            with self.app.config.get("SESSION_MAKER").begin() as session_:
                preference = ensure_notification_preference(
                    user=ensure_user(op="k1abc", session=session_),
                    session=session_,
                )
                preference.use_account_email_for_notifications = False
                preference.notification_email = "alerts@example.com"

            def _email_sender(message):
                captured_to["value"] = message.get("To")
                return "msg-1"

            result = dispatch_digest_notifications_for_batch(
                batch_id=batch_id,
                email_sender=_email_sender,
            )

            self.assertEqual(result["push_status"], "skipped")
            self.assertEqual(result["email_status"], "sent")
            self.assertEqual(captured_to["value"], "alerts@example.com")

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

    def test_dispatch_pending_skips_already_sent_batches(self):
        with self.app.app_context():
            old_batch_id = self._seed_user_and_batch(
                add_subscription=False,
                digest_date=date(2026, 2, 13),
            )
            new_batch_id = self._seed_user_and_batch(
                add_subscription=False,
                digest_date=date(2026, 2, 14),
            )
            with self.app.config.get("SESSION_MAKER").begin() as session_:
                user = ensure_user(op="k1abc", session=session_)
                session_.add(
                    NotificationDelivery(
                        user_id=user.id,
                        digest_batch_id=old_batch_id,
                        channel="web_push",
                        status="sent",
                    )
                )

            result = dispatch_pending_digest_notifications(limit=1)
            self.assertEqual(result["processed"], 1)

            with self.app.config.get("SESSION_MAKER").begin() as session_:
                new_batch_delivery = session_.scalar(
                    select(NotificationDelivery).where(
                        NotificationDelivery.digest_batch_id == new_batch_id,
                        NotificationDelivery.channel == "web_push",
                    )
                )
                self.assertIsNotNone(new_batch_delivery)

    def test_dispatch_pending_cleans_up_old_digest_rows(self):
        with self.app.app_context():
            self.app.config["DIGEST_RETENTION_DAYS"] = 1
            old_batch_id = self._seed_user_and_batch(
                add_subscription=False,
                digest_date=date(2020, 1, 1),
                qsl_count=1,
            )
            with self.app.config.get("SESSION_MAKER").begin() as session_:
                user = ensure_user(op="k1abc", session=session_)
                session_.add(
                    NotificationDelivery(
                        user_id=user.id,
                        digest_batch_id=old_batch_id,
                        channel="email",
                        status="failed",
                    )
                )

            dispatch_pending_digest_notifications(limit=10)

            with self.app.config.get("SESSION_MAKER").begin() as session_:
                old_batch = session_.scalar(
                    select(QSLDigestBatch).where(QSLDigestBatch.id == old_batch_id)
                )
                old_delivery = session_.scalar(
                    select(NotificationDelivery).where(
                        NotificationDelivery.digest_batch_id == old_batch_id
                    )
                )
                self.assertIsNone(old_batch)
                self.assertIsNone(old_delivery)


if __name__ == "__main__":
    unittest.main()
