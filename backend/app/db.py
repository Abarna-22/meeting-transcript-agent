import logging
import time
from functools import lru_cache

from sqlalchemy import Index, create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_settings

log = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


@lru_cache
def get_engine():
    url = get_settings().database_url
    kwargs = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **kwargs)


@lru_cache
def get_sessionmaker():
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_db():
    db = get_sessionmaker()()
    try:
        yield db
    finally:
        db.close()


def init_db(retries: int = 10, delay: float = 3.0) -> None:
    """Create tables. Retries so the API can start before MySQL is ready."""
    from . import models  # noqa: F401  (registers tables)

    for attempt in range(1, retries + 1):
        try:
            Base.metadata.create_all(get_engine())
            _migrate_user_username_column()
            _migrate_meeting_owner_column()
            return
        except Exception as exc:  # pragma: no cover - only hit when DB is down
            if attempt == retries:
                raise
            log.warning("Database not ready (%s). Retry %d/%d", exc, attempt, retries)
            time.sleep(delay)


def _migrate_user_username_column() -> None:
    engine = get_engine()
    if "username" not in {column["name"] for column in inspect(engine).get_columns("users")}:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE users ADD COLUMN username VARCHAR(80) NOT NULL DEFAULT ''"))
            if engine.dialect.name == "mysql":
                expression = "SUBSTR(email, 1, LOCATE('@', email) - 1)"
            else:
                expression = "SUBSTR(email, 1, INSTR(email, '@') - 1)"
            connection.execute(text(f"UPDATE users SET username = {expression} WHERE username = ''"))


def _migrate_meeting_owner_column() -> None:
    from .models import Meeting

    engine = get_engine()
    if "owner_id" not in {column["name"] for column in inspect(engine).get_columns("meetings")}:
        if engine.dialect.name == "sqlite":
            statement = "ALTER TABLE meetings ADD COLUMN owner_id INTEGER REFERENCES users (id)"
        elif engine.dialect.name == "mysql":
            statement = (
                "ALTER TABLE meetings ADD COLUMN owner_id INTEGER NULL, "
                "ADD CONSTRAINT fk_meetings_owner_id_users FOREIGN KEY (owner_id) REFERENCES users (id)"
            )
        else:
            statement = "ALTER TABLE meetings ADD COLUMN owner_id INTEGER NULL"
        with engine.begin() as connection:
            connection.execute(text(statement))
    Index("ix_meetings_owner_id", Meeting.owner_id).create(engine, checkfirst=True)
