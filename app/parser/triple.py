import re

from bs4 import BeautifulSoup
from flask import g, request

from ..dataclasses import TripleDetail
from ..urls import TRIPLE_PAGE_URL

STATES_COMPILED = re.compile(r"(?s).+ \((\w+)\)")


def triple() -> list[TripleDetail]:
    response = g.get("web_session").get(TRIPLE_PAGE_URL)

    op = request.cookies.get("op")
    soup = BeautifulSoup(response.content, "html.parser")

    # Parse the table to get rows
    triple_details: list[TripleDetail] = []
    rows = soup.select("table#creditsTable tbody tr")

    for row in rows:
        columns = row.find_all("td")

        triple_detail = TripleDetail(
            op=op,
            # reduce states to abbreviations
            state=re.sub(
                STATES_COMPILED,
                r"\1",
                columns[0].text,
            ),
            cw=str(columns[1].find("a"))
            .replace(' target="_new"', "")
            .replace(' target="+new"', "")
            if columns[1].find("a")
            else "-",
            phone=str(columns[2].find("a"))
            .replace(' target="_new"', "")
            .replace(' target="+new"', "")
            if columns[2].find("a")
            else "-",
            digital=str(columns[3].find("a"))
            .replace(' target="_new"', "")
            .replace(' target="+new"', "")
            if columns[3].find("a")
            else "-",
        )

        triple_details.append(triple_detail)

    return triple_details
