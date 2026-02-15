from datetime import timedelta
from logging import DEBUG, INFO, WARN
from os import getenv
from urllib.parse import urlsplit

import requests
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)

from .blueprints import api, auth, awards, billing, map, search
from .database import get_sessionmaker
from .lotw import LotwAuthExpiredError, LotwTransientError
from .regex_cache import REGEX_CACHE


def _env_flag(name: str, default: bool = False) -> bool:
    value = getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def create_app() -> Flask:
    app = Flask(__name__)
    app.name = "Mobile LOTW"

    # Check for required env vars
    common_message = (
        "OS Environment {} not found! Maybe you need to set a .env?"
    )
    if not getenv("MOBILE_LOTW_SECRET_KEY"):
        raise KeyError(common_message.format("MOBILE_LOTW_SECRET_KEY"))
    if not getenv("MOBILE_LOTW_DB_KEY"):
        raise KeyError(common_message.format("MOBILE_LOTW_DB_KEY"))
    if len(getenv("MOBILE_LOTW_DB_KEY")) != 16:
        raise ValueError("MOBILE_LOTW_DB_KEY must be 16 characters!")
    if not getenv("DB_URL"):
        raise ValueError("No DB_URL found.")
    if not getenv("API_KEY"):
        raise KeyError(common_message.format("API_KEY not found"))
    if not getenv("DEPLOY_SCRIPT_PATH"):
        raise KeyError(common_message.format("DEPLOY_SCRIPT_PATH not found"))

    # Check for optional env vars
    if not getenv("SESSION_CACHE_EXPIRATION"):
        app.logger.warning(
            "No SESSION_CACHE_EXPIRATION found. Defaulting to '30' minutes."
        )

    # Configure the application
    app.secret_key = getenv("MOBILE_LOTW_SECRET_KEY")
    app.permanent_session_lifetime = timedelta(days=365)

    app.config.from_mapping(
        MOBILE_LOTW_DB_KEY=getenv("MOBILE_LOTW_DB_KEY"),
        SESSION_MAKER=get_sessionmaker(getenv("DB_URL")),
        REQUEST_SESSION=requests.Session(),
        LOTW_REQUEST_TIMEOUT_SECONDS=int(
            getenv("LOTW_REQUEST_TIMEOUT_SECONDS")
            if getenv("LOTW_REQUEST_TIMEOUT_SECONDS")
            else 20
        ),
        QSO_IMPORT_MAX_WORKERS=int(
            getenv("QSO_IMPORT_MAX_WORKERS")
            if getenv("QSO_IMPORT_MAX_WORKERS")
            else 2
        ),
        SESSION_CACHE_EXPIRATION=int(getenv("SESSION_CACHE_EXPIRATION"))
        if getenv("SESSION_CACHE_EXPIRATION")
        else 30,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=_env_flag("MOBILE_LOTW_SECURE_COOKIES", False),
        REQUIRE_ACTIVE_SUBSCRIPTION=_env_flag(
            "REQUIRE_ACTIVE_SUBSCRIPTION", False
        ),
        BILLING_UI_ENABLED=_env_flag("BILLING_UI_ENABLED", False),
        REGEX_CACHE=REGEX_CACHE,
        WEB_PUSH_VAPID_PUBLIC_KEY=getenv("WEB_PUSH_VAPID_PUBLIC_KEY", ""),
        WEB_PUSH_VAPID_PRIVATE_KEY=getenv("WEB_PUSH_VAPID_PRIVATE_KEY", ""),
        WEB_PUSH_VAPID_SUBJECT=getenv("WEB_PUSH_VAPID_SUBJECT", ""),
        DIGEST_BASE_URL=getenv("DIGEST_BASE_URL", ""),
        DIGEST_SMTP_HOST=getenv("DIGEST_SMTP_HOST"),
        DIGEST_SMTP_PORT=int(getenv("DIGEST_SMTP_PORT", "587")),
        DIGEST_SMTP_USERNAME=getenv("DIGEST_SMTP_USERNAME"),
        DIGEST_SMTP_PASSWORD=getenv("DIGEST_SMTP_PASSWORD"),
        DIGEST_SMTP_FROM_EMAIL=getenv("DIGEST_SMTP_FROM_EMAIL", "info@mobilelotw.org"),
        DIGEST_SMTP_STARTTLS=_env_flag("DIGEST_SMTP_STARTTLS", True),
        DIGEST_NOTIFICATIONS_ENABLED=_env_flag("DIGEST_NOTIFICATIONS_ENABLED", True),
        WEB_PUSH_ENABLED=_env_flag("WEB_PUSH_ENABLED", True),
        DIGEST_EMAIL_ENABLED=_env_flag("DIGEST_EMAIL_ENABLED", True),
        DIGEST_DRY_RUN=_env_flag("DIGEST_DRY_RUN", False),
    )

    # Logging level
    app.logger.level = INFO

    # Primary routes
    @app.get("/")
    def home():
        if session.get("logged_in"):
            return redirect(url_for("awards.qsls"))
        return render_template("home.html")

    @app.get("/about")
    def about():
        return render_template("about.html")

    @app.get("/privacy")
    def privacy():
        return render_template("privacy.html")

    @app.get("/delete_account")
    def delete_account():
        return render_template("delete_account.html")

    @app.get("/qsl-digest-sw.js")
    def qsl_digest_service_worker():
        return send_from_directory(
            app.static_folder,
            "qsl_digest_sw.js",
            mimetype="application/javascript",
        )

    def _is_api_request() -> bool:
        return request.path.startswith("/api/")

    @app.errorhandler(LotwAuthExpiredError)
    def handle_lotw_auth_expired(error: LotwAuthExpiredError):
        app.logger.info("LoTW auth expired: %s", error)
        session.clear()

        if _is_api_request():
            return (
                jsonify(
                    {
                        "error": "lotw_auth_expired",
                        "message": "LoTW login expired. Please authenticate again.",
                    }
                ),
                401,
            )

        flash("LoTW login expired. Please log in again.", "info")
        next_page = request.endpoint
        if next_page in {None, "auth.login", "auth.logout"}:
            next_page = "awards.qsls"
        return redirect(url_for("auth.login", next_page=next_page))

    @app.errorhandler(LotwTransientError)
    def handle_lotw_transient_error(error: LotwTransientError):
        app.logger.warning("LoTW transient error: %s", error)

        if _is_api_request():
            status_code = error.status_code if error.status_code else 503
            return (
                jsonify(
                    {
                        "error": "lotw_unavailable",
                        "message": "LoTW is temporarily unavailable. Please retry.",
                    }
                ),
                status_code,
            )

        flash(
            "LoTW is temporarily unavailable. You are still logged in. Please try again soon.",
            "warning",
        )
        fallback = url_for("about")
        if request.referrer and urlsplit(request.referrer).path != request.path:
            return redirect(request.referrer)
        return redirect(fallback)

    # Blueprints
    app.register_blueprint(awards.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(billing.bp)
    app.register_blueprint(map.bp)
    app.register_blueprint(api.bp)
    app.register_blueprint(search.bp)

    return app
