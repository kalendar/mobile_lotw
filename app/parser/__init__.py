from flask import Request
from flask.ctx import _AppCtxGlobals

from .dxcc import dxcc
from .vucc import vucc
from .was import was
from .waz import waz
from .wpx import wpx


def parse_award(award: str, g=_AppCtxGlobals, request=Request):
    if award == "dxcc":
        return dxcc(g=g, request=request)
    elif award == "vucc":
        return vucc(g=g, request=request)
    elif award == "was":
        return was(g=g, request=request)
    elif award == "waz":
        return waz(g=g, request=request)
    elif award == "wpx":
        return wpx(g=g, request=request)
