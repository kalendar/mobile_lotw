from bs4 import BeautifulSoup
from flask import g, request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database.table_declarations import QSL
from ..urls import QSLS_PAGE_URL


def qsls(
    session: Session,
) -> tuple[list[QSL], list[QSL]]:
    response = g.web_session.get(QSLS_PAGE_URL)

    op = request.cookies.get("op")
    soup = BeautifulSoup(response.content, "html.parser")

    table = soup.select_one("form table")

    # Parse the table to get rows, remove some
    rows = table.find_all("tr")
    rows[28].decompose()
    rows[0].decompose()
    rows[1].decompose()
    rows[2].decompose()

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

    new_qsls: list[QSL] = []
    for current_qsl in current_qsls:
        if current_qsl not in previous_qsls:
            new_qsls.append(current_qsl)

    return new_qsls, previous_qsls
