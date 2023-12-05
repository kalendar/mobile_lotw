from flask import render_template, url_for

from ...cache import get_award_details
from ...urls import DXCC_PAGE_URL
from ..auth.wrappers import login_required
from .base import bp


@bp.get("/dxcc")
@login_required(next_page="awards.dxcc")
def dxcc():
    dxcc_details, parsed_at = get_award_details(award="dxcc")

    return render_template(
        "award.html",
        awards=dxcc_details,
        # Let user know when the data was parsed in a readable format
        parsed_at=parsed_at.strftime("%d/%m/%Y, %H:%M:%S"),
        # Let user reload at will
        force_reload=url_for("awards.dxcc", force_reload=True),
        page_url=DXCC_PAGE_URL,
        award_name="DXCC",
        title="DXCC Award Info",
    )
