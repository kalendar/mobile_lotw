from flask import g, render_template, request, session, url_for

from ...urls import WPX_PAGE_URL
from ...utils import get_award_details
from ..auth.wrappers import login_required
from .base import bp


@bp.get("/wpx")
@login_required(next_page="awards.wpx")
def wpx():
    wpx_details, wpx_parsed_at = get_award_details(
        award="waz",
        g=g,
        request=request,
        session=session,
    )

    return render_template(
        "award.html",
        awards=wpx_details,
        parsed_at=wpx_parsed_at.strftime("%d/%m/%Y, %H:%M:%S"),
        force_reload=url_for("awards.wpx", force_reload=True),
        page_url=WPX_PAGE_URL,
        award_name="WPX",
        title="WPX Award Info",
    )
