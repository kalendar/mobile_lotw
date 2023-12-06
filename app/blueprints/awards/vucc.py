from flask import render_template, url_for

from ...cache import get_award_details
from ...urls import VUCC_PAGE_URL
from ..auth.wrappers import login_required
from .base import bp


@bp.get("/vucc")
@login_required(next_page="awards.vucc")
def vucc():
    vucc_details, was_parsed_at = get_award_details(award="vucc")

    return render_template(
        "award.html",
        awards=vucc_details,
        # Let user know when the data was parsed in a readable format
        parsed_at=was_parsed_at.strftime("%d/%m/%Y, %H:%M:%S"),
        # Let user reload at will
        force_reload=url_for("awards.vucc", force_reload=True),
        page_url=VUCC_PAGE_URL,
        award_name="VUCC",
        title="VUCC Award Info",
    )
