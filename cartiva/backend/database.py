from collections.abc import Generator
from functools import lru_cache

from sqlalchemy.engine import Engine
from sqlmodel import Session, create_engine

from cartiva.backend.config import get_settings


@lru_cache
def get_engine() -> Engine:
    return create_engine(
        get_settings().database_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5},
        echo=False,
    )


def get_session() -> Generator[Session, None, None]:
    with Session(get_engine()) as session:
        yield session