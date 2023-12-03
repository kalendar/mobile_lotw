from flask import render_template, url_for

from ...cache import get_award_details
from ...urls import WAS_PAGE_URL
from ..auth.wrappers import login_required
from .base import bp


@bp.get("/was")
@login_required(next_page="awards.was")
def was():
    was_details, was_parsed_at = get_award_details(award="was")

    return render_template(
        "award.html",
        awards=was_details,
        parsed_at=was_parsed_at.strftime("%d/%m/%Y, %H:%M:%S"),
        force_reload=url_for("awards.was", force_reload=True),
        page_url=WAS_PAGE_URL,
        award_name="WAS",
        title="WAS Award Info",
    )
