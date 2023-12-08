from bs4 import BeautifulSoup
from flask import request

from .. import lotw
from ..dataclasses import AwardsDetail
from ..urls import WPX_PAGE_URL


def wpx() -> list[AwardsDetail]:
    response = lotw.get(WPX_PAGE_URL)

    op = request.cookies.get("op")
    soup = BeautifulSoup(response.content, "html.parser")

    # Parse the table to get rows
    wpx_details: list[AwardsDetail] = []
    rows = soup.select("table#accountStatusTable tbody tr")

    for row in rows:
        columns = row.find_all("td")

        wpx_detail = AwardsDetail(
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

        wpx_details.append(wpx_detail)

    return wpx_details
