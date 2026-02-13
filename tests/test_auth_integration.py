import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from requests import Response
from requests import RequestException
from requests.cookies import RequestsCookieJar

from app import create_app
from app.database.queries import ensure_user, get_user
from app.lotw import LotwTransientError


def _mock_login_response() -> Response:
    response = Response()
    response.status_code = 200
    response._content = b"<html><body>ok</body></html>"
    cookies = RequestsCookieJar()
    cookies.set("lotw_session", "cookie-value")
    response.cookies = cookies
    return response


class AuthIntegrationTests(unittest.TestCase):
    def setUp(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self._temp_dir.name) / "test.db"
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
        self.client = self.app.test_client()

    def tearDown(self):
        self._env.stop()
        self._temp_dir.cleanup()

    def _create_user(self, op: str, has_imported: bool = True) -> None:
        with self.app.app_context():
            with self.app.config.get("SESSION_MAKER").begin() as session_:
                user = ensure_user(op=op, session=session_)
                user.has_imported = has_imported
                user.lotw_cookies = {"lotw_session": "cookie-value"}
                session_.add(user)

    def _set_logged_in_session(self, op: str) -> None:
        with self.client.session_transaction() as flask_session:
            flask_session["logged_in"] = True
            flask_session["op"] = op

    def test_login_sets_persistent_session_cookie(self):
        op = "k1abc"
        self._create_user(op=op, has_imported=True)

        self.client.get("/login")
        with self.client.session_transaction() as flask_session:
            csrf_token = flask_session["login_csrf_token"]

        with patch("app.blueprints.auth.login.post", return_value=_mock_login_response()):
            response = self.client.post(
                "/login?next_page=awards.qsls",
                data={
                    "login": op,
                    "password": "secret",
                    "csrf_token": csrf_token,
                },
                follow_redirects=False,
            )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/qsls"))
        self.assertIn("Expires=", response.headers.get("Set-Cookie", ""))

        with self.client.session_transaction() as flask_session:
            self.assertTrue(flask_session.get("logged_in"))
            self.assertEqual(flask_session.get("op"), op)
            self.assertTrue(flask_session.permanent)

        home_response = self.client.get("/", follow_redirects=False)
        self.assertEqual(home_response.status_code, 302)
        self.assertTrue(home_response.headers["Location"].endswith("/qsls"))

    def test_transient_lotw_error_keeps_web_session(self):
        op = "k1xyz"
        self._create_user(op=op, has_imported=True)
        self._set_logged_in_session(op=op)

        with patch(
            "app.parser.dxcc.lotw.get",
            side_effect=LotwTransientError("LoTW temporarily unavailable."),
        ):
            response = self.client.get("/dxcc", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/about"))

        with self.client.session_transaction() as flask_session:
            self.assertTrue(flask_session.get("logged_in"))
            self.assertEqual(flask_session.get("op"), op)

    def test_transient_lotw_error_returns_api_503_and_keeps_session(self):
        op = "w1aw"
        self._create_user(op=op, has_imported=True)
        self._set_logged_in_session(op=op)

        with patch(
            "app.blueprints.api.import_qsos_data.import_qsos_for_user",
            side_effect=LotwTransientError("LoTW temporarily unavailable.", status_code=503),
        ):
            response = self.client.get("/api/v1/import_qsos_data")

        self.assertEqual(response.status_code, 503)
        payload = response.get_json()
        self.assertEqual(payload["error"], "lotw_unavailable")

        with self.client.session_transaction() as flask_session:
            self.assertTrue(flask_session.get("logged_in"))
            self.assertEqual(flask_session.get("op"), op)

    def test_transient_error_updates_health_metadata(self):
        op = "n0call"
        self._create_user(op=op, has_imported=True)
        self._set_logged_in_session(op=op)

        with patch(
            "app.lotw.r_get",
            side_effect=RequestException("network down"),
        ):
            response = self.client.get("/dxcc", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/about"))

        with self.app.app_context():
            with self.app.config.get("SESSION_MAKER").begin() as session_:
                user = get_user(op=op, session=session_)
                self.assertEqual(user.lotw_auth_state, "transient_error")
                self.assertEqual(user.lotw_fail_count, 1)
                self.assertEqual(user.lotw_last_fail_reason, "request_exception")
                self.assertIsNotNone(user.lotw_last_fail_at)

    def test_map_endpoint_handles_empty_cached_map_data(self):
        op = "k9map"
        self._create_user(op=op, has_imported=True)
        self._set_logged_in_session(op=op)

        response = self.client.get("/api/v1/get_map_data?json=true")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload, {})


class SubscriptionGateTests(unittest.TestCase):
    def setUp(self):
        self._temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self._temp_dir.name) / "test_subs.db"
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
                "REQUIRE_ACTIVE_SUBSCRIPTION": "1",
            },
            clear=False,
        )
        self._env.start()
        self.app = create_app()
        self.app.config.update(TESTING=True)
        self.client = self.app.test_client()

        with self.app.app_context():
            with self.app.config.get("SESSION_MAKER").begin() as session_:
                user = ensure_user(op="nogold", session=session_)
                user.has_imported = True
                user.lotw_cookies = {"lotw_session": "cookie-value"}
                session_.add(user)

        with self.client.session_transaction() as flask_session:
            flask_session["logged_in"] = True
            flask_session["op"] = "nogold"

    def tearDown(self):
        self._env.stop()
        self._temp_dir.cleanup()

    def test_paid_api_route_returns_402_when_subscription_required(self):
        response = self.client.get("/api/v1/get_map_data?json=true")
        self.assertEqual(response.status_code, 402)
        payload = response.get_json()
        self.assertEqual(payload["error"], "subscription_required")

    def test_paid_web_route_redirects_to_billing_when_subscription_required(self):
        response = self.client.get("/map", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/billing", response.headers["Location"])


if __name__ == "__main__":
    unittest.main()
