# QSL Digest Notifications Implementation Plan

This plan adds a paid feature that notifies users about new LoTW QSLs with:

- primary channel: web push notifications (website/browser)
- fallback channel: email
- deterministic destination: `/qsl/digest?date=YYYY-MM-DD`

The phases are intentionally ordered for low-risk delivery and easy rollback.

## Scope and assumptions

- Only users with active entitlement can enable digest notifications.
- Existing encrypted LoTW cookie storage on `users.lotw_cookies_b` remains the source of LoTW auth for polling.
- Digest cadence for v1 is daily, at user-configured local time.
- Push and email must reference the same digest snapshot to avoid mismatches.

## Phase 1: Migrations and models

Goal: create persistence needed for preferences, subscriptions, digest snapshots, and delivery audit.

### 1.1 Add user profile fields

`users` table additions:

- `timezone` (`VARCHAR`, nullable initially, default `"UTC"` for backfill)
- `locale` (`VARCHAR`, nullable)
- `email_verified_at` (`TIMESTAMP WITH TIME ZONE`, nullable) if not already available through existing auth flow

Model touchpoint:

- `app/database/table_declarations/user.py`

### 1.2 Notification preferences table

Create `notification_preferences` (1 row per user):

- `id` PK
- `user_id` FK unique -> `users.id`
- `qsl_digest_enabled` (`BOOLEAN`, default `false`)
- `qsl_digest_time_local` (`TIME`, default `08:00`)
- `qsl_digest_frequency` (`VARCHAR`, default `"daily"`)
- `fallback_to_email` (`BOOLEAN`, default `true`)
- `quiet_hours_start_local` (`TIME`, nullable)
- `quiet_hours_end_local` (`TIME`, nullable)
- `last_digest_cursor_at` (`TIMESTAMP WITH TIME ZONE`, nullable)
- `created_at`, `updated_at`

### 1.3 Web push subscriptions table

Create `web_push_subscriptions` (multi-device/browser per user):

- `id` PK
- `user_id` FK -> `users.id`
- `endpoint` (`TEXT`, unique)
- `p256dh_key` (`TEXT`)
- `auth_key` (`TEXT`)
- `status` (`VARCHAR`, default `"active"`) values: `active`, `invalid`, `unsubscribed`
- `user_agent` (`TEXT`, nullable)
- `platform` (`VARCHAR`, nullable)
- `last_seen_at` (`TIMESTAMP WITH TIME ZONE`, nullable)
- `last_success_at` (`TIMESTAMP WITH TIME ZONE`, nullable)
- `last_failure_at` (`TIMESTAMP WITH TIME ZONE`, nullable)
- `failure_count` (`INTEGER`, default `0`)
- `created_at`, `updated_at`

### 1.4 Digest snapshot table

Create `qsl_digest_batches` (deterministic digest payload per user/day):

- `id` PK
- `user_id` FK -> `users.id`
- `digest_date` (`DATE`) in user-local date
- `window_start_utc` (`TIMESTAMP WITH TIME ZONE`)
- `window_end_utc` (`TIMESTAMP WITH TIME ZONE`)
- `qsl_count` (`INTEGER`, default `0`)
- `payload_json` (`JSONB`) compact list of QSO IDs + metadata
- `generated_at` (`TIMESTAMP WITH TIME ZONE`)
- unique index: `(user_id, digest_date)`

### 1.5 Delivery audit/idempotency table

Create `notification_deliveries`:

- `id` PK
- `user_id` FK -> `users.id`
- `digest_batch_id` FK -> `qsl_digest_batches.id`, nullable (for diagnostic sends)
- `type` (`VARCHAR`, default `"qsl_digest"`)
- `channel` (`VARCHAR`) values: `web_push`, `email`
- `status` (`VARCHAR`) values: `queued`, `sent`, `failed`, `skipped`
- `provider_message_id` (`VARCHAR`, nullable)
- `error_code` (`VARCHAR`, nullable)
- `error_detail` (`TEXT`, nullable)
- `sent_at` (`TIMESTAMP WITH TIME ZONE`, nullable)
- `created_at`
- unique index: `(user_id, digest_batch_id, channel)`

### 1.6 ORM + query support

Add model files and query helpers under:

- `app/database/table_declarations/`
- `app/database/queries/`

Update exports:

- `app/database/table_declarations/__init__.py`
- `app/database/queries/__init__.py`

### 1.7 Migration files

Add Alembic migration(s) in:

- `alembic/versions/`

Acceptance criteria:

- `alembic upgrade head` succeeds
- new tables and indexes exist
- app starts with no model import errors

## Phase 2: LoTW auth persistence hardening

Goal: safely support unattended daily checks with current cookie-based auth.

### 2.1 Reuse existing encrypted cookie storage

- Keep `users.lotw_cookies_b` as auth source for workers.
- Add explicit states for digest eligibility based on LoTW health fields:
  - `ok`
  - `auth_expired`
  - `transient_error`

Touchpoints:

- `app/lotw.py`
- `app/database/table_declarations/user.py`

### 2.2 Eligibility and reauth behavior

Add helper logic (service/query layer) to classify users as:

- eligible for digest sync (`lotw_auth_state == "ok"` and digest enabled)
- blocked pending reauth (`auth_expired`)
- temporarily deferred (transient failures with retry/backoff)

### 2.3 Security guardrails

- confirm no plaintext LoTW cookies are logged
- add/update logging redaction where needed
- ensure disconnect flow can wipe stored LoTW cookie blob

Acceptance criteria:

- background sync skips users with expired auth and records reason
- users in expired state are prompted to login again before digest resumes

## Phase 3: Incremental QSL detection and digest batch generation

Goal: generate one deterministic digest batch per user/day.

### 3.1 New service module

Create service(s), for example:

- `app/services/qsl_digest.py`

Responsibilities:

- determine UTC window from user timezone + configured digest time
- query newly received QSLs for the window (using `qso_reports.app_lotw_rxqsl`)
- upsert `qsl_digest_batches`
- update `notification_preferences.last_digest_cursor_at`

### 3.2 Scheduler entrypoint

Add scheduled worker entrypoint that:

- scans users with enabled digest preference
- selects users due to run now (timezone-aware)
- generates or refreshes today’s digest batch

Potential touchpoints:

- `app/background_jobs.py` (or new dedicated scheduler module)

### 3.3 Idempotency and dedupe

- rerunning batch generation for same user/date updates existing row, does not duplicate
- no notification send until a batch exists and `qsl_count > 0`

Acceptance criteria:

- repeated scheduler runs produce one batch per user/date
- digest counts match QSO query results for the target window

## Phase 4: Notification fanout (web push first, email fallback)

Goal: deliver digest reliably across channels with observable outcomes.

### 4.1 Web push channel

Add a push service (e.g., using `pywebpush`) to:

- send notification payload to all active subscriptions for the user
- update subscription health on success/failure
- mark 404/410 subscriptions as `invalid`

Suggested module:

- `app/services/web_push.py`

### 4.2 Email fallback channel

Add digest email sender:

- send only if push not possible or push attempts failed per policy
- require user email (and verification if enforced)
- include link to digest page URL with date param

Suggested module:

- `app/services/digest_email.py`

### 4.3 Delivery orchestrator

Create orchestrator service:

- consumes `qsl_digest_batches`
- enforces channel order: push then fallback email
- writes `notification_deliveries`
- applies idempotency constraint per channel

Acceptance criteria:

- users with valid subscriptions receive push
- users without valid push receive email fallback
- duplicate sends are prevented by DB constraints + logic

## Phase 5: Website UX and endpoints

Goal: provide settings, subscription registration, and deterministic destination page.

### 5.1 Notification settings page (single destination)

Add UI and routes for:

- enable/disable daily digest
- select local delivery time
- toggle email fallback
- choose notification email destination (separate from billing email)
- configure timezone
- browser push opt-in status

Use `/notifications/settings` as the single destination:

- free users: show settings as read-only plus inline billing checkout options
- paid users: show editable settings and subscription management entrypoint

### 5.2 Web push subscription API

Add endpoints:

- `POST /api/v1/notifications/web-push/subscribe`
- `POST /api/v1/notifications/web-push/unsubscribe`
- optional `POST /api/v1/notifications/web-push/heartbeat`

Expected payload:

- `endpoint`, `p256dh`, `auth`, device metadata

### 5.3 Service worker

Add service worker script in static assets:

- receive push event
- show notification
- handle `notificationclick` to open/focus digest page URL

Touchpoints:

- `app/static/` (service worker file)
- template that registers service worker and requests permission

### 5.4 Digest destination page

Add route:

- `GET /qsl/digest?date=YYYY-MM-DD`

Behavior:

- require login
- fetch `qsl_digest_batches` for user/date
- render exact QSLs represented in `payload_json`
- display fallback message if batch not found

Touchpoints:

- new blueprint handler (likely under `app/blueprints/awards/`)
- new template (e.g., `app/templates/qsl_digest.html`)

### 5.5 Email template

Add digest email template rendering with:

- count summary
- top entries
- link to `/qsl/digest?date=...`

Acceptance criteria:

- user can opt in from website only (no mobile app dependency)
- clicking push/email opens exact digest batch view

## Phase 6: Metrics, operations, and rollout controls

Goal: run safely in production and debug quickly.

### 6.1 Logging and metrics

Track:

- digest jobs due/running/completed
- batch generation counts
- push success/failure rates
- fallback email usage rate
- LoTW auth-expired population

### 6.2 Operational controls

Add env flags:

- `DIGEST_NOTIFICATIONS_ENABLED`
- `WEB_PUSH_ENABLED`
- `DIGEST_EMAIL_ENABLED`
- `DIGEST_DRY_RUN` (logs intended sends without sending)
- `DIGEST_RETENTION_DAYS` (delete old digest snapshots + deliveries)

### 6.3 Admin/debug tooling (lightweight)

At minimum, add internal logs or a limited endpoint for:

- last digest batch per user
- last delivery per channel
- last LoTW sync/auth state

Acceptance criteria:

- feature can be turned off globally without rollback
- failures are visible and attributable

## Phase 7: Tests

Goal: cover core behavior before broader rollout.

### 7.1 Unit tests

Add tests for:

- timezone window calculations
- digest dedupe/idempotency
- push-vs-email fallback decision logic
- subscription invalidation on hard failures

Location:

- `tests/` (new test modules)

### 7.2 Integration tests

Add tests for end-to-end backend flow:

- create user + preferences + mock new QSLs
- generate digest batch
- orchestrate sends
- verify `notification_deliveries` rows

### 7.3 UI/API tests (light)

Add tests for:

- subscribe/unsubscribe API validation
- digest page access and not-found handling

Acceptance criteria:

- tests pass locally
- core workflows have regression coverage

## Rollout plan

1. Deploy schema and dark-launch code paths behind flags.
2. Internal testing with a small set of real users.
3. Enable for paid beta cohort only.
4. Observe delivery metrics and LoTW auth-expired rates for 1-2 weeks.
5. Expand to all paid users.

## Production runbook (required)

### 1) Install/update dependencies

From the project root on prod:

```sh
.venv/bin/pip install -r requirements.txt
```

This now includes `pywebpush` for web-push delivery.

### 2) Configure environment variables

Required for this feature:

- `DIGEST_NOTIFICATIONS_ENABLED`
- `WEB_PUSH_ENABLED`
- `DIGEST_EMAIL_ENABLED`
- `DIGEST_DRY_RUN`
- `DIGEST_RETENTION_DAYS`
- `WEB_PUSH_VAPID_PUBLIC_KEY`
- `WEB_PUSH_VAPID_PRIVATE_KEY`
- `WEB_PUSH_VAPID_SUBJECT`
- `DIGEST_BASE_URL`
- `DIGEST_SMTP_HOST`
- `DIGEST_SMTP_PORT`
- `DIGEST_SMTP_USERNAME`
- `DIGEST_SMTP_PASSWORD`
- `DIGEST_SMTP_FROM_EMAIL`
- `DIGEST_SMTP_STARTTLS`

Reference defaults are documented in `example.env`.

### 3) Run DB migrations

This feature depends on:

- `20260214_03_qsl_digest_notification_foundation.py`
- `20260215_04_notification_email_preferences.py`

```sh
.venv/bin/alembic upgrade head
```

Expected new objects:

- table `notification_preferences`
- table `web_push_subscriptions`
- table `qsl_digest_batches`
- table `notification_deliveries`
- new `users` columns:
  - `email_verified_at`
  - `timezone`
  - `locale`

### 4) Safe rollout sequence

1. Deploy with:
   - `DIGEST_NOTIFICATIONS_ENABLED=1`
   - `WEB_PUSH_ENABLED=0`
   - `DIGEST_EMAIL_ENABLED=0`
   - `DIGEST_DRY_RUN=1`
2. Verify digest generation logs and table writes only.
3. Enable push:
   - `WEB_PUSH_ENABLED=1`
4. Enable email fallback:
   - `DIGEST_EMAIL_ENABLED=1`
5. Disable dry-run:
   - `DIGEST_DRY_RUN=0`

### 5) Post-deploy checks

1. Visit `/notifications/settings` as a free user and confirm locked settings + inline billing.
2. Complete checkout and return to `/notifications/settings`.
3. As a paid user, save settings including preferred notification email.
4. Subscribe/unsubscribe browser push and verify `web_push_subscriptions` updates.
5. Confirm digest generation creates/updates `qsl_digest_batches`.
6. Confirm dispatch writes `notification_deliveries` rows for `web_push` and/or `email`.
7. Open `/qsl/digest?date=YYYY-MM-DD` and verify the list matches `payload_json`.

## File-by-file execution map

Likely files to add/update in order:

1. `alembic/versions/<new_migration>.py`
2. `app/database/table_declarations/user.py`
3. `app/database/table_declarations/<new_models>.py`
4. `app/database/table_declarations/__init__.py`
5. `app/database/queries/<new_queries>.py`
6. `app/services/qsl_digest.py`
7. `app/services/web_push.py`
8. `app/services/digest_email.py`
9. `app/background_jobs.py` (or new scheduler module)
10. `app/blueprints/api/<notifications_api>.py`
11. `app/blueprints/awards/<digest_route>.py`
12. `app/templates/<settings_and_digest_templates>.html`
13. `app/static/<service_worker>.js`
14. `tests/<new_test_files>.py`
15. `example.env` and docs updates

## Open decisions to resolve before coding

- Which email provider to use (SMTP vs API provider).
- Which web-push library/provider to standardize on.
- Whether email verification is mandatory before fallback sends.
- Paid gating UX resolved: read-only settings + inline billing on `/notifications/settings`.
