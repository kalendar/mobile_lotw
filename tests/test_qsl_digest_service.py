from datetime import datetime, time, timezone
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_app
from app.database.queries import (
    ensure_notification_preference,
    ensure_user,
    get_digest_batch,
    get_notification_preference,
    get_user,
)
from app.database.table_declarations import QSOReport
from app.services.qsl_digest import compute_digest_schedule, run_due_qsl_digest_generation


class QSLDigestServiceTests(unittest.TestCase):
    def setUp(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self._temp_dir.name) / "test_digest.db"
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
        self.app.config.update(TESTING=True)

    def tearDown(self):
        self._env.stop()
        self._temp_dir.cleanup()

    def test_compute_digest_schedule_uses_local_timezone_and_cursor(self):
        now_utc = datetime(2026, 2, 14, 15, 0, tzinfo=timezone.utc)
        cursor = datetime(2026, 2, 13, 14, 0, tzinfo=timezone.utc)
        schedule = compute_digest_schedule(
            now_utc=now_utc,
            timezone_name="America/Chicago",
            digest_time_local=time(8, 0),
            last_digest_cursor_at=cursor,
        )

        self.assertEqual(schedule.digest_date.isoformat(), "2026-02-14")
        self.assertEqual(schedule.window_end_utc.isoformat(), "2026-02-14T14:00:00+00:00")
        self.assertEqual(schedule.window_start_utc.isoformat(), cursor.isoformat())

    def test_run_due_generation_upserts_digest_batch(self):
        now_utc = datetime(2026, 2, 14, 9, 0, tzinfo=timezone.utc)
        with self.app.app_context():
            with self.app.config.get("SESSION_MAKER").begin() as session_:
                user = ensure_user(op="k1abc", session=session_)
                user.subscription_status = "active"
                user.timezone = "UTC"
                user.lotw_auth_state = "ok"
                user.lotw_cookies_b = b"encrypted-cookie-data"
                session_.add(user)
                session_.flush()
                preference = ensure_notification_preference(user=user, session=session_)
                preference.qsl_digest_enabled = True
                preference.qsl_digest_time_local = time(8, 0)

                session_.add(
                    QSOReport(
                        user_id=user.id,
                        call="W1AW",
                        app_lotw_qso_timestamp=datetime(
                            2026, 2, 14, 1, 0, tzinfo=timezone.utc
                        ),
                        app_lotw_rxqsl=datetime(
                            2026, 2, 14, 7, 59, tzinfo=timezone.utc
                        ),
                    )
                )
                session_.add(
                    QSOReport(
                        user_id=user.id,
                        call="N0CALL",
                        app_lotw_qso_timestamp=datetime(
                            2026, 2, 13, 1, 0, tzinfo=timezone.utc
                        ),
                        app_lotw_rxqsl=datetime(
                            2026, 2, 13, 7, 59, tzinfo=timezone.utc
                        ),
                    )
                )

            first = run_due_qsl_digest_generation(now_utc=now_utc)
            self.assertEqual(first["created"], 1)
            self.assertEqual(first["updated"], 0)

            second = run_due_qsl_digest_generation(now_utc=now_utc)
            self.assertEqual(second["created"], 0)
            self.assertEqual(second["updated"], 1)

            with self.app.config.get("SESSION_MAKER").begin() as session_:
                user = get_user(op="k1abc", session=session_)
                preference = get_notification_preference(user_id=user.id, session=session_)
                self.assertIsNotNone(preference)
                batch = get_digest_batch(
                    user_id=user.id,
                    digest_date=datetime(2026, 2, 14).date(),
                    session=session_,
                )
                self.assertIsNotNone(batch)
                self.assertEqual(batch.qsl_count, 1)
                self.assertEqual(len(batch.payload_json["qso_ids"]), 1)
                self.assertEqual(batch.payload_json["items"][0]["call"], "W1AW")
                self.assertTrue(
                    preference.last_digest_cursor_at.isoformat().startswith(
                        "2026-02-14T08:00:00"
                    )
                )


if __name__ == "__main__":
    unittest.main()
