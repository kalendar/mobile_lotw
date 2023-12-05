import re

from bs4 import BeautifulSoup
from flask import current_app, g, request

from ..dataclasses import Row
from ..urls import ACCOUNT_CREDITS_URL


def account_credits() -> tuple[str, list[Row], str, str]:
    url_args = (
        "awg_id="
        + request.args.get("awg_id")
        + "&ac_acct="
        + request.args.get("ac_acct")
        + "&aw_id="
        + request.args.get("aw_id")
        + "&ac_view=allc"
    )

    response = g.web_session.get(f"{ACCOUNT_CREDITS_URL}{url_args}")

    if request.args.get("awg_id") == "WAS":
        # Pass WAS to the table in the view on the next page
        table_header = lookup_label(request.args.get("aw_id"))

    elif request.args.get("awg_id") == "WAZ":
        # Pass WAZ to the table in the view on the next page
        table_header = lookup_label(request.args.get("aw_id"))

    elif request.args.get("awg_id") == "VUCC":
        if request.args.get("aw_id") == "FFMA":
            table_header = "Fred Fish Memorial Award"
        else:
            table_header = lookup_label(request.args.get("aw_id"))

    elif request.args.get("awg_id") == "WPX":
        # Pass WPX to the table in the view on the next page
        table_header = lookup_label(request.args.get("aw_id"))

    else:
        # Pass DXCC to the table in the view on the next page
        table_header = lookup_dxcc_label(request.args.get("aw_id"))

    soup = BeautifulSoup(response.content, "html.parser")
    table = soup.find("table", attrs={"id": "creditsTable"})

    rows = table.find_all("tr")
    award_details: list[Row] = []

    for row in rows[1:]:
        columns = row.find_all("td")
        if not columns:
            continue
        if request.args.get("awg_id") == "WAS":
            award_detail = Row(
                label=re.sub(
                    current_app.config["REGEX_CACHE"]["STATES_COMPILED"],
                    r"\1",
                    columns[0].text,
                ),
                value=str(columns[1].find("a"))
                .replace(' target="_new"', "")
                .replace(' target="+new"', "")
                if columns[1].find("a")
                else columns[1].text,
            )

        elif request.args.get("awg_id") == "WAZ":
            award_detail = Row(
                label=columns[0].text,
                value=str(columns[1].find("a"))
                .replace(' target="_new"', "")
                .replace(' target="+new"', "")
                if columns[1].find("a")
                else columns[1].text,
            )

        elif request.args.get("awg_id") == "DXCC":
            award_detail = Row(
                label=columns[0].text,
                value=str(columns[1].find("a"))
                .replace(' target="_new"', "")
                .replace(' target="+new"', "")
                if columns[1].find("a")
                else columns[1].text,
            )

        award_details.append(award_detail)

    award: str = request.args.get("awg_id")
    title: str = request.args.get("awg_id") + " All Credits"

    return award, award_details, title, table_header


def lookup_dxcc_label(arg):
    if arg == "DXCC-M":
        return "Mixed"
    elif arg == "DXCC-CW":
        return "CW"
    elif arg == "DXCC-PH":
        return "Phone"
    elif arg == "DXCC-RTTY":
        return "Digital"
    elif arg == "DXCC-SAT":
        return "Satellite"
    elif arg == "DXCC-160":
        return "160M"
    elif arg == "DXCC-80":
        return "80M"
    elif arg == "DXCC-40":
        return "40M"
    elif arg == "DXCC-30":
        return "30M"
    elif arg == "DXCC-20":
        return "20M"
    elif arg == "DXCC-17":
        return "17M"
    elif arg == "DXCC-15":
        return "15M"
    elif arg == "DXCC-12":
        return "12M"
    elif arg == "DXCC-10":
        return "10M"
    elif arg == "DXCC-6":
        return "6M"
    elif arg == "DXCC-2":
        return "2M"
    elif arg == "DXCC-3CM":
        return "3CM"
    elif arg == "DXCC-13CM":
        return "13CM"
    elif arg == "DXCC-70CM":
        return "70CM"
    elif arg == "DXCC-23CM":
        return "23CM"
    elif arg == "DXCC-CHAL":
        return "Challenge"
    else:
        return "Worked"


def lookup_label(arg):
    if arg.count("-") == 0:
        return "Mixed"
    elif arg.count("-") == 1:
        band = arg.split("-")[1]
        if band[-1] == "M":
            return band
        elif band[0].isdigit():
            return band + "M"
        else:
            return band
    elif arg.count("-") == 2:
        x, band, mode = arg.split("-")
        if band[0].isdigit():
            return band + "M " + mode
        else:
            return band + " " + mode
    else:
        return "Worked"
