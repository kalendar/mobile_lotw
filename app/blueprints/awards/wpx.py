from flask import render_template, url_for

from ...cache import get_award_details
from ...urls import WPX_PAGE_URL
from ..auth.wrappers import login_required
from .base import bp


@bp.get("/wpx")
@login_required(next_page="awards.wpx")
def wpx():
    wpx_details, wpx_parsed_at = get_award_details(award="wpx")

    return render_template(
        "award.html",
        awards=wpx_details,
        # Let user know when the data was parsed in a readable format
        parsed_at=wpx_parsed_at.strftime("%d/%m/%Y, %H:%M:%S"),
        # Let user reload at will
        force_reload=url_for("awards.wpx", force_reload=True),
        page_url=WPX_PAGE_URL,
        award_name="WPX",
        title="WPX Award Info",
    )
