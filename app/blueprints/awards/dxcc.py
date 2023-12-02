from flask import g, render_template, request, session, url_for

from ...urls import DXCC_PAGE_URL
from ...utils import get_award_details
from ..auth.wrappers import login_required
from .base import bp


@bp.get("/dxcc")
@login_required(next_page="awards.dxcc")
def dxcc():
    dxcc_details, dxcc_parsed_at = get_award_details(
        award="dxcc",
        g=g,
        request=request,
        session=session,
    )

    return render_template(
        "award.html",
        awards=dxcc_details,
        parsed_at=dxcc_parsed_at.strftime("%d/%m/%Y, %H:%M:%S"),
        force_reload=url_for("awards.dxcc", force_reload=True),
        page_url=DXCC_PAGE_URL,
        award_name="DXCC",
        title="DXCC Award Info",
    )
