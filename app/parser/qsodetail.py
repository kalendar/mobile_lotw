from bs4 import BeautifulSoup
from flask import g, request

from ..dataclasses import QSODetail, Row
from ..urls import DETAILS_PAGE_URL


def qsodetail() -> QSODetail:
    response = g.web_session.get(DETAILS_PAGE_URL + request.args.get("qso"))

    soup = BeautifulSoup(response.content, "html.parser")

    page_header = soup.find("h3")
    qso_table = page_header.findNext("table")

    rows = qso_table.find_all("tr")

    qso_detail = QSODetail()

    for row in rows:
        tds = row.find_all("td")
        if len(tds) == 3:
            current_row = Row(label=tds[0].text, value=tds[-1].text)
            qso_detail.rows.append(current_row)

    return qso_detail
