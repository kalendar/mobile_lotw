from datetime import datetime, timedelta

import requests
from flask import (
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from ...urls import LOGIN_URL
from .base import bp


@bp.route(
    "/login/",
    defaults={"next_page": "awards.dxcc"},
    methods=["POST", "GET"],
)
@bp.route(
    "/login/<next_page>",
    methods=["POST", "GET"],
)
def login(next_page: str):
    if request.method == "POST":
        payload = {
            "login": request.form.get("login"),
            "password": request.form.get("password"),
            "acct_sel": "",
            "thisForm": "login",
        }

        request_session = requests.Session()
        login_response = request_session.post(LOGIN_URL, data=payload)

        if "postcard" in login_response.text:
            flash("LOTW login unsuccessful! Please try again.", "error")
            if next_page:
                return redirect(url_for("auth.login", next_page=next_page))
            else:
                return redirect(url_for("auth.login"))

        else:
            session.update(
                {
                    "web_session_cookies": requests.utils.dict_from_cookiejar(
                        request_session.cookies
                    ),
                    "logged_in": True,
                }
            )

            expiration_date = datetime.now() + timedelta(days=365)

            response = redirect(url_for(next_page))
            response.set_cookie(
                key="op",
                value=request.form.get("login").lower(),
                expires=expiration_date,
            )

            return response

    else:
        if g.get("web_session"):
            return redirect(url_for("awards.dxcc"))

        else:
            return render_template(
                "login.html",
                title="Login to Mobile LotW",
            )
