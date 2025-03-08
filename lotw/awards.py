from dataclasses import dataclass
from typing import Type

from database.table_declarations.user import User
from env import SETTINGS
from lotw.util import convert_table, get


@dataclass
class Award:
    name: str
    new_qsls: str
    in_process_qsls: str
    credits_awarded: str
    total: str

    def values(self) -> list[str]:
        return [
            self.name,
            self.new_qsls,
            self.in_process_qsls,
            self.credits_awarded,
            self.total,
        ]


class WAS(Award):
    pass


class VUCC(Award):
    pass


class WPX(Award):
    pass


class WAZ(Award):
    pass


@dataclass
class DXCC:
    name: str
    new_qsls: str
    in_process_qsls: str
    credits_awarded: str
    total_all: str
    total_current: str


def retrieve_award[T](url: str, user: User, award: Type[T]) -> list[T]:
    response = get(
        url=url,
        cookies=user.get_lotw_cookies(SETTINGS.database_key),
    )

    return convert_table(
        text=response.content.decode(encoding="utf-8"), record_type=award
    )
