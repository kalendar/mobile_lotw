from flask import render_template, url_for

from ...cache import get_award_details
from ...urls import TRIPLE_PAGE_URL
from ..auth.wrappers import login_required
from .base import bp


@bp.get("/triple")
@login_required(next_page="awards.triple")
def triple():
    triple_details, was_parsed_at = get_award_details(award="triple")

    return render_template(
        "triple.html",
        triples=triple_details,
        parsed_at=was_parsed_at.strftime("%d/%m/%Y, %H:%M:%S"),
        force_reload=url_for("awards.triple", force_reload=True),
        triple_page_url=TRIPLE_PAGE_URL,
        title="Triple Play Award Info",
    )
