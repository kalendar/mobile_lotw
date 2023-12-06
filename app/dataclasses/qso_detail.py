from dataclasses import dataclass, field

from .row import Row


@dataclass
class QSODetail:
    rows: list[Row] = field(default_factory=list)
