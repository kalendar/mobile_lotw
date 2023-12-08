from ..dataclasses import AwardsDetail, TripleDetail
from .account_credits import account_credits
from .dxcc import dxcc
from .qsodetail import qsodetail
from .triple import triple
from .vucc import vucc
from .was import was
from .waz import waz
from .wpx import wpx


def parse_award(
    award: str,
) -> list[AwardsDetail] | list[TripleDetail]:
    """Given the name of an award, return a list of its details.

    Args:
        award (str): Award name
        g (_AppCtxGlobals): Flask current g.
        request (Request): Flask current request.

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
