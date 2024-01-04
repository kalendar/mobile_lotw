from datetime import timedelta
from logging import DEBUG, INFO, WARN
from os import getenv

import requests
from flask import Flask, render_template, session, redirect, url_for

from .blueprints import api, auth, awards, map, search
from .database import get_sessionmaker
from .regex_cache import REGEX_CACHE


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

    # Check for optional env vars
    if not getenv("SESSION_CACHE_EXPIRATION"):
        app.logger.warn(
            "No SESSION_CACHE_EXPIRATION found. Defaulting to '30' minutes."
        )

    # Configure the application
    app.secret_key = getenv("MOBILE_LOTW_SECRET_KEY")
    app.permanent_session_lifetime = timedelta(days=365)

    app.config.from_mapping(
        MOBILE_LOTW_DB_KEY=getenv("MOBILE_LOTW_DB_KEY"),
        SESSION_MAKER=get_sessionmaker(getenv("DB_URL")),
        REQUEST_SESSION=requests.Session(),
        SESSION_CACHE_EXPIRATION=int(getenv("SESSION_CACHE_EXPIRATION"))
        if getenv("SESSION_CACHE_EXPIRATION")
        else 30,
        REGEX_CACHE=REGEX_CACHE,
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

    # Blueprints
    app.register_blueprint(awards.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(map.bp)
    app.register_blueprint(api.bp)
    app.register_blueprint(search.bp)

    return app
