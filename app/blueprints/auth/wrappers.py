from functools import wraps

from flask import current_app, flash, jsonify, redirect, request, session, url_for

from ...database.queries import get_user


ALLOWED_NEXT_PAGES: frozenset[str] = frozenset(
    {
        "awards.accountcredits",
        "awards.dxcc",
        "awards.find",
        "awards.qsls",
        "awards.qsl_digest",
        "awards.triple",
        "awards.vucc",
        "awards.was",
        "awards.waz",
        "awards.wpx",
        "billing.notification_settings",
        "billing.overview",
        "map.view",
        "search.callsign",
    }
)


def sanitize_next_page(next_page: str | None, default: str = "awards.qsls") -> str:
    if not next_page:
        return default
    if next_page in ALLOWED_NEXT_PAGES:
        return next_page
    return default


def login_required(next_page: str = "awards.qsls"):
    def decorator(view):
        @wraps(view)
        def decorated_view(*args, **kwargs):
            # If the user is not logged in
            if not session.get("logged_in") or not session.get("op"):
                session.clear()
                # Request login
                flash("Please login.", "info")
                return redirect(
                    url_for(
                        "auth.login",
                        next_page=sanitize_next_page(next_page=next_page),
                    )
                )
            # Else, move forward
            return view(*args, **kwargs)

        return decorated_view

    return decorator


def paid_required(next_page: str = "billing.notification_settings"):
    def decorator(view):
        @wraps(view)
        def decorated_view(*args, **kwargs):
            if not session.get("logged_in") or not session.get("op"):
                session.clear()
                flash("Please login.", "info")
                return redirect(url_for("auth.login", next_page="awards.qsls"))

            # Gate only when explicitly enabled.
            if not current_app.config.get("REQUIRE_ACTIVE_SUBSCRIPTION", False):
                return view(*args, **kwargs)

            with current_app.config.get("SESSION_MAKER").begin() as session_:
                user = get_user(op=session.get("op"), session=session_)
                if not user.has_active_entitlement:
                    if request.path.startswith("/api/"):
                        return (
                            jsonify(
                                {
                                    "error": "subscription_required",
                                    "message": "An active subscription is required.",
                                }
                            ),
                            402,
                        )
                    flash("An active subscription is required for this feature.", "warning")
                    return redirect(
                        url_for(
                            sanitize_next_page(
                                next_page=next_page,
                                default="billing.notification_settings",
                            )
                        )
                    )
            return view(*args, **kwargs)

        return decorated_view

    return decorator
