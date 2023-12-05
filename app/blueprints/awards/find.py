import re

from flask import current_app, g, render_template, request

from ...urls import FIND_PAGE_URL
from ..auth.wrappers import login_required
from .base import bp

MATCH_YES = re.compile(
    r"Last upload for <b>[^<]+</b>&#58; \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}Z"
)
MATCH_NO = re.compile(r"Last upload for <b>[^<]+</b>&#58; No log data found")


@bp.route("/find", methods=["GET", "POST"])
@login_required(next_page="find")
def find():
    # If requesting
    if request.method == "POST":
        act = request.form.get("act")

        # Send request to LOTW and store response
        response = g.web_session.post(FIND_PAGE_URL, data={"act": act})

        if "Last upload" in response.text:
            match_yes = re.search(
                current_app.config["REGEX_CACHE"]["MATCH_YES"],
                response.text,
            )
            match_no = re.search(
                current_app.config["REGEX_CACHE"]["MATCH_NO"],
                response.text,
            )

            if match_yes:
                last_upload_info = match_yes.group(0).replace(
                    "&#58;", "&#58;<br />"
                )
            elif match_no:
                last_upload_info = match_no.group(0).replace(
                    "&#58;", "&#58;<br />"
                )
            else:
                last_upload_info = "Please enter a call sign."

            return render_template(
                "find.html",
                results=last_upload_info,
                title="Logbook Call Sign Activity",
            )
        else:
            return render_template(
                "find.html",
                error_msg="There was an error. Please try again.",
                title="Logbook Call Sign Activity",
            )
    else:
        return render_template(
            "find.html",
            title="Logbook Call Sign Activity",
        )
