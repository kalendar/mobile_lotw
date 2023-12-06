from dataclasses import dataclass


@dataclass
class AwardsDetail:
    op: str
    award: str
    new: str
    in_process: str
    awarded: str
    total: str
