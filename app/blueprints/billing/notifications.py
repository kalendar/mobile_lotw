from datetime import datetime
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
from ..auth.wrappers import login_required, paid_required
from .base import bp

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


def _is_valid_timezone(tz_name: str) -> bool:
    try:
        ZoneInfo(tz_name)
        return True
    except ZoneInfoNotFoundError:
        return False


@bp.route("/notifications/settings", methods=["GET", "POST"])
@login_required()
@paid_required(next_page="billing.overview")
def notification_settings():
    with current_app.config.get("SESSION_MAKER").begin() as session_:
        user = get_user(op=session.get("op"), session=session_)
        preference = ensure_notification_preference(user=user, session=session_)

        if request.method == "POST":
            timezone_input = request.form.get("timezone", type=str, default="").strip()
            if timezone_input and _is_valid_timezone(timezone_input):
                user.timezone = timezone_input
            elif timezone_input:
                flash("Invalid timezone. Use an IANA timezone like America/Chicago.", "error")

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

            preference.qsl_digest_enabled = bool(request.form.get("qsl_digest_enabled"))
            preference.fallback_to_email = bool(request.form.get("fallback_to_email"))

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
        )
