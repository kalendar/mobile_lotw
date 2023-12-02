from flask import g, render_template, request, session, url_for

from ...urls import WAZ_PAGE_URL
from ...utils import get_award_details
from ..auth.wrappers import login_required
from .base import bp


@bp.get("/waz")
@login_required(next_page="awards.waz")
def waz():
    waz_details, waz_parsed_at = get_award_details(
        award="waz",
        g=g,
        request=request,
        session=session,
    )

    return render_template(
        "award.html",
        awards=waz_details,
        parsed_at=waz_parsed_at.strftime("%d/%m/%Y, %H:%M:%S"),
        force_reload=url_for("awards.waz", force_reload=True),
        page_url=WAZ_PAGE_URL,
        award_name="WAZ",
        title="WAZ Award Info",
    )
