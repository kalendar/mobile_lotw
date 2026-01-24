from requests import Response as RResponse

from ..dataclasses import AwardsDetail, TripleDetail
from ..urls import (
    DXCC_PAGE_URL,
    TRIPLE_PAGE_URL,
    VUCC_PAGE_URL,
    WAS_PAGE_URL,
    WAZ_PAGE_URL,
    WPX_PAGE_URL,
)
from .account_credits import account_credits
from .dxcc import dxcc, parse_dxcc_response
from .qsodetail import qsodetail
from .triple import parse_triple_response, triple
from .vucc import parse_vucc_response, vucc
from .was import parse_was_response, was
from .waz import parse_waz_response, waz
from .wpx import parse_wpx_response, wpx

# Mapping of award names to their URLs and parse functions
AWARD_PARSERS = {
    "dxcc": (DXCC_PAGE_URL, parse_dxcc_response),
    "was": (WAS_PAGE_URL, parse_was_response),
    "waz": (WAZ_PAGE_URL, parse_waz_response),
    "wpx": (WPX_PAGE_URL, parse_wpx_response),
    "vucc": (VUCC_PAGE_URL, parse_vucc_response),
    "triple": (TRIPLE_PAGE_URL, parse_triple_response),
}


def parse_award(
    award: str,
) -> list[AwardsDetail] | list[TripleDetail]:
    """Given the name of an award, return a list of its details.

    Args:
        award (str): Award name

    Returns:
        list[AwardsDetail]: List of award details
    """
    if award == "dxcc":
        return dxcc()
    elif award == "triple":
        return triple()
    elif award == "vucc":
        return vucc()
    elif award == "was":
        return was()
    elif award == "waz":
        return waz()
    elif award == "wpx":
        return wpx()


def parse_award_from_response(
    award: str, response: RResponse
) -> list[AwardsDetail] | list[TripleDetail]:
    """Parse award details from a pre-fetched response.

    Args:
        award: Award name (dxcc, was, waz, wpx, vucc, triple)
        response: Pre-fetched HTTP response

    Returns:
        Parsed award details
    """
    if award not in AWARD_PARSERS:
        raise ValueError(f"Unknown award: {award}")
    _, parse_func = AWARD_PARSERS[award]
    return parse_func(response)
