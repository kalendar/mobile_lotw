from bs4 import BeautifulSoup
from flask import Request
from flask.ctx import _AppCtxGlobals

from ..awards_dataclass import AwardsDetail
from ..urls import DXCC_PAGE_URL


def vucc(g: _AppCtxGlobals, request: Request) -> list[AwardsDetail]:
    response = g.web_session.get(DXCC_PAGE_URL)

    op = request.cookies.get("op")
    soup = BeautifulSoup(response.content, "html.parser")

    # Parse the table to get rows
    vucc_details: list[AwardsDetail] = []
    rows = soup.select("table#accountStatusTable tbody tr")

    for row in rows:
        columns = row.find_all("td")

        current_row = AwardsDetail(
            op=op,
            award=str(columns[0].find("a"))
            .replace(' target="_new"', "")
            .replace(' target="+new"', "")
            if columns[0].find("a")
            else columns[0].text,
            new=columns[1].text,
            in_process=columns[2].text,
            awarded=columns[3].text,
            total=columns[4].text,
        )

        vucc_details.append(current_row)

    return vucc_details
