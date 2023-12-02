from configparser import ConfigParser
from datetime import timedelta
from os import getenv

import requests
from flask import Flask, g, render_template, session

from .blueprints import auth, awards
from .blueprints.find import find
from .blueprints.qsodetail import qsodetail
from .database import get_sessionmaker


def create_app() -> Flask:
    app = Flask(__name__)

    app.secret_key = getenv("MOBILE_LOTW_SECRET_KEY")
    app.permanent_session_lifetime = timedelta(days=365)

    app.config.from_mapping(
        SESSION_MAKER=get_sessionmaker(getenv("DB_NAME")),
        REQUEST_SESSION=requests.Session(),
    )

    @app.before_request
    def before_request():
        if session.get("web_session_cookies"):
            g.web_session = app.config.get("REQUEST_SESSION")
            g.web_session.cookies = requests.utils.cookiejar_from_dict(
                session.get("web_session_cookies")
            )
        else:
            g.web_session = None

    @app.get("/")
    def home():
        return render_template("home.html")

    @app.get("/about")
    def about():
        return render_template("about.html")

    @app.get("/privacy")
    def privacy():
        return render_template("privacy.html")

    app.register_blueprint(awards.bp)
    app.register_blueprint(auth.bp)

    app.add_url_rule("/find", view_func=find, methods=["GET", "POST"])
    app.add_url_rule("/qsodetail", view_func=qsodetail, methods=["GET"])

    return app
