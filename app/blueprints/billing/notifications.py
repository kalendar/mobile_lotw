from datetime import datetime
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import (
    current_app,
    flash,
    render_template,
    request,
    session,
    url_for,
)

from ...database.queries import (
    ensure_notification_preference,
    get_active_web_push_subscriptions,
    get_user,
)
from ..auth.wrappers import login_required
from .base import bp
from .overview import _stripe_price_options, _stripe_ready

TIMEZONE_OPTIONS: tuple[tuple[str, str], ...] = (
    ("UTC", "UTC"),
    ("America/New_York", "America/New_York (Eastern)"),
    ("America/Chicago", "America/Chicago (Central)"),
    ("America/Denver", "America/Denver (Mountain)"),
    ("America/Los_Angeles", "America/Los_Angeles (Pacific)"),
    ("America/Anchorage", "America/Anchorage (Alaska)"),
    ("Pacific/Honolulu", "Pacific/Honolulu (Hawaii)"),
    ("Europe/London", "Europe/London"),
    ("Europe/Paris", "Europe/Paris"),
    ("Europe/Berlin", "Europe/Berlin"),
    ("Asia/Tokyo", "Asia/Tokyo"),
    ("Asia/Seoul", "Asia/Seoul"),
    ("Asia/Singapore", "Asia/Singapore"),
    ("Asia/Kolkata", "Asia/Kolkata"),
    ("Australia/Sydney", "Australia/Sydney"),
    ("Pacific/Auckland", "Pacific/Auckland"),
)


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _is_valid_timezone(tz_name: str) -> bool:
    try:
        ZoneInfo(tz_name)
        return True
    except ZoneInfoNotFoundError:
        return False


def _is_valid_email(value: str) -> bool:
    return bool(EMAIL_PATTERN.match(value))


@bp.route("/notifications/settings", methods=["GET", "POST"])
@login_required()
def notification_settings():
    checkout_state = request.args.get("checkout", type=str, default="").strip().lower()
    if checkout_state == "success":
        flash("Subscription checkout completed. Refreshing plan status may take a moment.", "success")
    elif checkout_state == "cancel":
        flash("Checkout was canceled.", "info")

    with current_app.config.get("SESSION_MAKER").begin() as session_:
        user = get_user(op=session.get("op"), session=session_)
        preference = ensure_notification_preference(user=user, session=session_)
        has_paid_access = user.has_active_entitlement
        stripe_ready = bool(current_app.config.get("BILLING_UI_ENABLED", False)) and _stripe_ready()
        price_options = _stripe_price_options()

        if request.method == "POST":
            if not has_paid_access:
                flash(
                    "An active subscription is required to change notification settings.",
                    "warning",
                )
            else:
                has_error = False
                timezone_input = request.form.get(
                    "timezone",
                    type=str,
                    default="",
                ).strip()
                if timezone_input and _is_valid_timezone(timezone_input):
                    user.timezone = timezone_input
                elif timezone_input:
                    flash(
                        "Invalid timezone. Use an IANA timezone like America/Chicago.",
                        "error",
                    )
                    has_error = True

                locale_input = request.form.get("locale", type=str, default="").strip()
                user.locale = locale_input or None

                time_input = request.form.get("qsl_digest_time_local", type=str, default="")
                if time_input:
                    try:
                        preference.qsl_digest_time_local = datetime.strptime(
                            time_input, "%H:%M"
                        ).time()
                    except ValueError:
                        flash("Invalid digest time. Use HH:MM format.", "error")
                        has_error = True

                preference.qsl_digest_enabled = bool(
                    request.form.get("qsl_digest_enabled")
                )
                preference.fallback_to_email = bool(
                    request.form.get("fallback_to_email")
                )

                use_account_email = bool(
                    request.form.get("use_account_email_for_notifications")
                )
                preference.use_account_email_for_notifications = use_account_email
                notification_email = request.form.get(
                    "notification_email",
                    type=str,
                    default="",
                ).strip()

                if notification_email and not _is_valid_email(notification_email):
                    flash("Notification email is invalid.", "error")
                    has_error = True
                elif use_account_email:
                    preference.notification_email = None
                else:
                    preference.notification_email = notification_email or None

                if (
                    preference.fallback_to_email
                    and not preference.notification_email
                    and not (user.email or "").strip()
                    and preference.use_account_email_for_notifications
                ):
                    flash(
                        "Fallback email is enabled, but your account email is empty.",
                        "warning",
                    )

                if not has_error:
                    flash("Notification settings saved.", "success")

        active_subscriptions = get_active_web_push_subscriptions(
            user_id=user.id, session=session_
        )
        timezone_options = list(TIMEZONE_OPTIONS)
        current_timezone = user.timezone or "UTC"
        known_timezones = {value for value, _ in timezone_options}
        if current_timezone not in known_timezones:
            timezone_options.insert(0, (current_timezone, f"{current_timezone} (Current)"))
        return render_template(
            "notification_settings.html",
            title="Notification Settings",
            user=user,
            preference=preference,
            timezone_options=timezone_options,
            web_push_public_key=current_app.config.get("WEB_PUSH_VAPID_PUBLIC_KEY", ""),
            active_web_push_count=len(active_subscriptions),
            user_op=user.op,
            settings_url=url_for("billing.notification_settings"),
            has_paid_access=has_paid_access,
            stripe_ready=stripe_ready,
            price_options=price_options,
            can_manage_subscription=bool(user.stripe_customer_id) and stripe_ready,
            subscription={
                "tier": user.plan_tier,
                "status": user.subscription_status,
                "current_period_end": user.subscription_current_period_end,
                "entitlement_expires_at": user.entitlement_expires_at,
            },
        )
