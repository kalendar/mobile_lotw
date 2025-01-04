from sqlalchemy import Engine, create_engine

from env import SETTINGS

from .table_declarations import Base


def make_engine(connection_string: str = SETTINGS.database_connection) -> Engine:
    return create_engine(connection_string)


def make_tables(engine: Engine | None = None) -> None:
    if not engine:
        engine = make_engine()
    Base.metadata.create_all(engine)


def drop_tables(engine: Engine | None = None) -> None:
    if not engine:
        engine = make_engine()
    Base.metadata.drop_all(engine)
