from bs4 import BeautifulSoup
from flask import request

from .. import lotw
from ..dataclasses import QSODetail, Row
from ..urls import DETAILS_PAGE_URL


def qsodetail() -> QSODetail:
    qso = request.args.get("qso", type=str, default="").strip()
    qso_detail = QSODetail()
    if not qso:
        return qso_detail

    response = lotw.get(DETAILS_PAGE_URL + qso)

    soup = BeautifulSoup(response.content, "html.parser")
    page_header = soup.find("h3")
    if not page_header:
        return qso_detail

    qso_table = page_header.find_next("table")
    if not qso_table:
        return qso_detail
    rows = qso_table.find_all("tr")

    for row in rows:
        tds = row.find_all("td")
        if len(tds) == 3:
            current_row = Row(label=tds[0].text, value=tds[-1].text)
            qso_detail.rows.append(current_row)

    return qso_detail
