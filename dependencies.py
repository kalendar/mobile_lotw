from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session, create_session

from database import make_engine


def get_session() -> Session:  # type:ignore
    engine = make_engine()
    with create_session(engine) as session:
        yield session  # type:ignore


def get_session_begin() -> Session:  # type:ignore
    engine = make_engine()
    with create_session(engine) as session, session.begin():
        yield session  # type:ignore


SessionDep = Annotated[Session, Depends(get_session)]
SessionBeginDep = Annotated[Session, Depends(get_session_begin)]
