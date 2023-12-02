import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine.base import Engine
from sqlalchemy.orm import sessionmaker

from .table_declarations import Base


def db_file_present(instance_path: str, db_name: str) -> bool:
    """
    Check if DB file exists.

    Args:
        instance_path (str): Path to DB file.

    Returns:
        bool: If exists.
    """
    return os.path.exists(os.path.join(instance_path, db_name))


def create_db_file(instance_path: str, db_name: str):
    """
    Create DB file at give path.

    Args:
        instance_path (str): Path to create file.
    """
    os.makedirs(os.path.join(instance_path), exist_ok=True)

    with open(
        os.path.join(instance_path, db_name), "w", encoding="utf-8"
    ) as file:
        file.close()


def create_db(instance_path: str, db_name: str) -> Engine:
    """
    Create DB and initialize tables/engine.

    Args:
        instance_path (str): Path to DB.
    """

    create_db_file(instance_path, db_name)
    engine: Engine = set_engine(instance_path, db_name)
    Base.metadata.create_all(bind=engine)
    return engine


def set_engine(instance_path: str, db_name: str) -> Engine:
    """
    Set DB engine to DB file path.

    Args:
        instance_path (str): Path to DB file.
    """
    return create_engine("sqlite:///" + os.path.join(instance_path, db_name))


def create_session(engine: Engine) -> sessionmaker:
    """
    Create session from sessionmaker.

    Args:
        engine (Engine): Engine linked to DB

    Returns:
        sessionmaker: sessionmaker.
    """
    return sessionmaker(bind=engine, future=True)


def init_db(instance_path: str, db_name: str) -> sessionmaker:
    """
    Initialize DB, will create DB if not in existence.

    Args:
        instance_path (str): Path to DB file.
        db_name (str): Name of DB file.

    Returns:
        sessionmaker: sessionmaker.
    """
    if not db_file_present(instance_path, db_name):
        engine: Engine = create_db(instance_path, db_name)
    else:
        engine: Engine = set_engine(instance_path, db_name)

    return create_session(engine)


def get_sessionmaker(db_name) -> sessionmaker:
    return init_db((Path(__file__) / "../../../").resolve(), db_name)
