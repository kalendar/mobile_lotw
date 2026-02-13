from flask import flash, redirect, render_template, url_for

from ...parser import account_credits
from ..auth.wrappers import login_required
from .base import bp


@bp.get("/accountcredits")
@login_required(next_page="awards.accountcredits")
def accountcredits():
    award, award_details, title, table_header = account_credits()
    if award == "Unknown":
        flash("Unable to load account credits for that request.", "warning")
        return redirect(url_for("awards.qsls"))

    return render_template(
        "award_details.html",
        award=award,
        table_header=table_header,
        award_details=award_details,
        title=title,
    )
