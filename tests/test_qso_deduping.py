from datetime import datetime, timezone
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app import create_app
from app.database.queries import ensure_user
from app.database.queries.qso_page import get_25_most_recent_rxqsls
from app.database.table_declarations import QSOReport
from app.services.qso_import import _add_reports_to_db


class QSODedupingTests(unittest.TestCase):
    def setUp(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self._temp_dir.name) / "test_qso_deduping.db"
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

    def test_add_reports_to_db_collapses_duplicate_payload_rows(self):
        with self.app.app_context():
            with self.app.config.get("SESSION_MAKER").begin() as session_:
                user = ensure_user(op="k1abc", session=session_)
                user.has_imported = False
                session_.add(user)
                session_.flush()

                ts = datetime(2026, 2, 19, 12, 0, tzinfo=timezone.utc)
                qso_without_qsl = SimpleNamespace(
                    call="W1AW",
                    app_lotw_qso_timestamp=ts,
                    app_lotw_rxqso=None,
                    app_lotw_rxqsl=None,
                )
                qso_with_qsl = SimpleNamespace(
                    call="W1AW",
                    app_lotw_qso_timestamp=ts,
                    app_lotw_rxqso=ts,
                    app_lotw_rxqsl=ts,
                )
                inserted, updated = _add_reports_to_db(
                    qso_reports=[qso_without_qsl, qso_with_qsl],
                    user_id=user.id,
                    has_imported=False,
                    session_=session_,
                )
                self.assertEqual(inserted, 1)
                self.assertEqual(updated, 0)

            with self.app.config.get("SESSION_MAKER").begin() as session_:
                rows = session_.query(QSOReport).all()
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0].call, "W1AW")
                self.assertEqual(
                    rows[0].app_lotw_qso_timestamp.replace(tzinfo=timezone.utc),
                    ts,
                )

    def test_get_25_most_recent_rxqsls_hides_duplicate_rows(self):
        with self.app.app_context():
            with self.app.config.get("SESSION_MAKER").begin() as session_:
                user = ensure_user(op="k1abc", session=session_)
                session_.add(user)
                session_.flush()

                ts = datetime(2026, 2, 19, 12, 0, tzinfo=timezone.utc)
                ts2 = datetime(2026, 2, 19, 12, 1, tzinfo=timezone.utc)
                session_.add(
                    QSOReport(
                        user_id=user.id,
                        call="W1AW",
                        app_lotw_qso_timestamp=ts,
                        app_lotw_rxqsl=ts2,
                    )
                )
                session_.add(
                    QSOReport(
                        user_id=user.id,
                        call="W1AW",
                        app_lotw_qso_timestamp=ts,
                        app_lotw_rxqsl=ts2,
                    )
                )
                session_.add(
                    QSOReport(
                        user_id=user.id,
                        call="K9XYZ",
                        app_lotw_qso_timestamp=ts2,
                        app_lotw_rxqsl=ts2,
                    )
                )

            with self.app.config.get("SESSION_MAKER").begin() as session_:
                user = ensure_user(op="k1abc", session=session_)
                qsls = get_25_most_recent_rxqsls(user=user, session=session_)
                keys = {(qso.app_lotw_qso_timestamp, qso.call) for qso in qsls}
                self.assertEqual(len(qsls), 2)
                self.assertEqual(len(keys), 2)


if __name__ == "__main__":
    unittest.main()
