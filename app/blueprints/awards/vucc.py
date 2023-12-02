from flask import g, render_template, request, session, url_for

from ...urls import VUCC_PAGE_URL
from ...utils import get_award_details
from ..auth.wrappers import login_required
from .base import bp


@bp.get("/vucc")
@login_required(next_page="awards.vucc")
def vucc():
    vucc_details, was_parsed_at = get_award_details(
        award="vucc",
        g=g,
        request=request,
        session=session,
    )

    return render_template(
        "award.html",
        awards=vucc_details,
        parsed_at=was_parsed_at.strftime("%d/%m/%Y, %H:%M:%S"),
        force_reload=url_for("awards.vucc", force_reload=True),
        page_url=VUCC_PAGE_URL,
        award_name="VUCC",
        title="VUCC Award Info",
    )
