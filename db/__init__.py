"""Database package: models, connection/session helpers, and CRUD.

Kept intentionally light — importing ``db`` does NOT pull in ``core`` (and thus
langgraph). The pipeline-persistence wrapper lives in ``db.service`` and must be
imported explicitly::

    from db.service import generate_and_save
"""

from __future__ import annotations

from .connection import (
    get_database_url,
    get_engine,
    get_session_factory,
    init_db,
    reset_engine,
    session_scope,
)
from .crud import (
    create_generation,
    delete_generation,
    get_generation,
    list_generations,
    update_generation,
)
from .models import Base, BlogGeneration

__all__ = [
    "Base",
    "BlogGeneration",
    "get_database_url",
    "get_engine",
    "get_session_factory",
    "init_db",
    "reset_engine",
    "session_scope",
    "create_generation",
    "get_generation",
    "list_generations",
    "update_generation",
    "delete_generation",
]
