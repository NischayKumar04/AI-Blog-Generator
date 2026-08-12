"""Database engine / session management.

Reads ``DATABASE_URL`` from the environment. When unset, defaults to a local
SQLite file so the app and tests run with no database server. In the container
(Phase 4) ``DATABASE_URL`` points at Postgres and the same code path is used.

The engine and session factory are created lazily and cached module-level, so
importing this package touches no database. ``reset_engine()`` exists mainly for
tests, which repoint ``DATABASE_URL`` at a throwaway SQLite file per test.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base

DEFAULT_DATABASE_URL = "sqlite:///./bloggen.db"

_engine: Optional[Engine] = None
_session_factory: Optional[sessionmaker] = None


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        url = get_database_url()
        connect_args = {}
        if url.startswith("sqlite"):
            # allow use across threads (Streamlit runs callbacks off-thread)
            connect_args["check_same_thread"] = False
        _engine = create_engine(url, connect_args=connect_args, future=True)
    return _engine


def get_session_factory() -> sessionmaker:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=get_engine(), expire_on_commit=False, future=True
        )
    return _session_factory


def init_db() -> None:
    """Create all tables if they do not already exist. Idempotent."""
    Base.metadata.create_all(get_engine())


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transactional session: commits on success, rolls back on error."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_engine() -> None:
    """Dispose and clear the cached engine/factory (used by tests)."""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None
