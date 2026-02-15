from datetime import datetime, timedelta, timezone
import unittest

from app.database.table_declarations import NotificationPreference, User
from app.services.digest_eligibility import evaluate_digest_eligibility


class DigestEligibilityTests(unittest.TestCase):
    def _build_user(self) -> User:
        user = User(op="k1abc")
        user.subscription_status = "active"
        user.lotw_cookies_b = b"encrypted-cookie-data"
        user.lotw_auth_state = "ok"
        return user

    def _build_pref(self) -> NotificationPreference:
        preference = NotificationPreference(user_id=1)
        preference.qsl_digest_enabled = True
        return preference

    def test_missing_preference_is_not_eligible(self):
        user = self._build_user()
        eligibility = evaluate_digest_eligibility(user=user, preference=None)
        self.assertFalse(eligibility.eligible)
        self.assertEqual(eligibility.reason, "missing_preference")

    def test_digest_disabled_is_not_eligible(self):
        user = self._build_user()
        preference = self._build_pref()
        preference.qsl_digest_enabled = False
        eligibility = evaluate_digest_eligibility(user=user, preference=preference)
        self.assertFalse(eligibility.eligible)
        self.assertEqual(eligibility.reason, "digest_disabled")

    def test_inactive_entitlement_is_not_eligible(self):
        user = self._build_user()
        user.subscription_status = "inactive"
        preference = self._build_pref()
        eligibility = evaluate_digest_eligibility(user=user, preference=preference)
        self.assertFalse(eligibility.eligible)
        self.assertEqual(eligibility.reason, "inactive_entitlement")

    def test_auth_expired_is_not_eligible(self):
        user = self._build_user()
        user.lotw_auth_state = "auth_expired"
        preference = self._build_pref()
        eligibility = evaluate_digest_eligibility(user=user, preference=preference)
        self.assertFalse(eligibility.eligible)
        self.assertEqual(eligibility.reason, "lotw_auth_expired")

    def test_transient_error_with_backoff_is_deferred(self):
        user = self._build_user()
        user.lotw_auth_state = "transient_error"
        user.lotw_fail_count = 2
        user.lotw_last_fail_at = datetime.now(tz=timezone.utc)
        preference = self._build_pref()

        eligibility = evaluate_digest_eligibility(user=user, preference=preference)
        self.assertFalse(eligibility.eligible)
        self.assertEqual(eligibility.reason, "lotw_transient_backoff")
        self.assertIsNotNone(eligibility.retry_at)

    def test_transient_error_after_backoff_is_eligible(self):
        user = self._build_user()
        user.lotw_auth_state = "transient_error"
        user.lotw_fail_count = 1
        user.lotw_last_fail_at = datetime.now(tz=timezone.utc) - timedelta(hours=1)
        preference = self._build_pref()

        eligibility = evaluate_digest_eligibility(user=user, preference=preference)
        self.assertTrue(eligibility.eligible)
        self.assertEqual(eligibility.reason, "eligible")

    def test_missing_cookie_blob_is_not_eligible(self):
        user = self._build_user()
        user.lotw_cookies_b = None
        preference = self._build_pref()

        eligibility = evaluate_digest_eligibility(user=user, preference=preference)
        self.assertFalse(eligibility.eligible)
        self.assertEqual(eligibility.reason, "lotw_auth_missing")


if __name__ == "__main__":
    unittest.main()
