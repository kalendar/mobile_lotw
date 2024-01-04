from sqlalchemy import create_engine
from sqlalchemy.engine.base import Engine
from sqlalchemy.orm import sessionmaker

from .table_declarations import Base


def create_db(engine: Engine | None = None, url: str | None = None) -> None:
    if not engine:
        engine = create_engine(url=url)
    Base.metadata.create_all(bind=engine)


def drop_db(engine: Engine | None = None, url: str | None = None) -> None:
    if not engine:
        engine = create_engine(url=url)

    Base.metadata.drop_all(bind=engine)


def get_sessionmaker(url: str) -> sessionmaker:
    engine = create_engine(url=url)
    create_db(engine=engine)

    return sessionmaker(bind=engine, future=True)
