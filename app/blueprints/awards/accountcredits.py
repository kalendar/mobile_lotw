from flask import g, render_template, request

from ...parser import account_credits
from ..auth.wrappers import login_required
from .base import bp


@bp.get("/accountcredits")
@login_required(next_page="awards.accountcredits")
def accountcredits():
    award, award_details, title, table_header = account_credits()

    return render_template(
        "award_details.html",
        award=award,
        table_header=table_header,
        award_details=award_details,
        title=title,
    )
