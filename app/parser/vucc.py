from bs4 import BeautifulSoup
from flask import session
from requests import Response as RResponse

from .. import lotw
from ..dataclasses import AwardsDetail
from ..urls import VUCC_PAGE_URL


def vucc() -> list[AwardsDetail]:
    """Fetch and parse VUCC award page."""
    response = lotw.get(VUCC_PAGE_URL)
    return parse_vucc_response(response)


def parse_vucc_response(response: RResponse) -> list[AwardsDetail]:
    """Parse a pre-fetched VUCC response."""
    op = session.get("op", "")
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
