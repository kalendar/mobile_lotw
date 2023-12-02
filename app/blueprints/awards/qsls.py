from bs4 import BeautifulSoup
from flask import (
    current_app,
    g,
    render_template,
    request,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...database.table_declarations import QSL
from ...urls import QSLS_PAGE_URL
from ..auth.wrappers import login_required
from .base import bp


@bp.get("/qsls")
@login_required(next_page="awards.qsls")
def qsls():
    response = g.web_session.get(QSLS_PAGE_URL)
    op = request.cookies.get("op")
    soup = BeautifulSoup(response.content, "html.parser")
    form = soup.find("form")
    table = form.find("table")

    # Parse the table to get rows, remove some
    rows = table.find_all("tr")
    rows[28].decompose()
    rows[0].decompose()
    rows[1].decompose()
    rows[2].decompose()

    with current_app.config.get("SESSION_MAKER").begin() as session:
        session: Session

        rows = table.find_all("tr")

        current_qsls: list[QSL] = []
        for row in rows:
            columns = row.find_all("td")
            current_row = QSL(
                op=op,
                worked=columns[2].text,
                band=columns[4].text,
                mode=columns[5].text,
                details=str(columns[0].find("a"))
                .replace(' target="_new"', "")
                .replace(' target="+new"', ""),
            )
            current_qsls.append(current_row)

        get_all_qsl_for_op = select(QSL).where(QSL.op == op)

        previous_qsls: list[QSL] = session.scalars(get_all_qsl_for_op).all()

        for previous_qsl in previous_qsls:
            session.delete(previous_qsl)

        session.add_all(current_qsls)

        new_qsls = []
        for current_qsl in current_qsls:
            if current_qsl not in previous_qsls:
                new_qsls.append(current_qsl)

        return render_template(
            "qsls.html",
            new_qsls=new_qsls,
            previous_qsls=previous_qsls,
            qsls_page_url=QSLS_PAGE_URL,
            title="25 Most Recent QSLs",
        )
