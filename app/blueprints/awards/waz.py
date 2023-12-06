from flask import render_template, url_for

from ...cache import get_award_details
from ...urls import WAZ_PAGE_URL
from ..auth.wrappers import login_required
from .base import bp


@bp.get("/waz")
@login_required(next_page="awards.waz")
def waz():
    waz_details, was_parsed_at = get_award_details(award="waz")

    return render_template(
        "award.html",
        awards=waz_details,
        # Let user know when the data was parsed in a readable format
        parsed_at=was_parsed_at.strftime("%d/%m/%Y, %H:%M:%S"),
        # Let user reload at will
        force_reload=url_for("awards.waz", force_reload=True),
        page_url=WAZ_PAGE_URL,
        award_name="WAZ",
        title="WAZ Award Info",
    )
