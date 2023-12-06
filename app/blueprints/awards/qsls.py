from flask import current_app, render_template

from ...parser import qsls as parse_qsls
from ...urls import QSLS_PAGE_URL
from ..auth.wrappers import login_required
from .base import bp


@bp.get("/qsls")
@login_required(next_page="awards.qsls")
def qsls():
    with current_app.config.get("SESSION_MAKER").begin() as session:
        new_qsls, previous_qsls = parse_qsls(session=session)

        return render_template(
            "qsls.html",
            new_qsls=new_qsls,
            previous_qsls=previous_qsls,
            qsls_page_url=QSLS_PAGE_URL,
            title="25 Most Recent QSLs",
        )
