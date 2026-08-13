"""Create/read/update/list/delete operations for ``BlogGeneration`` rows.

Each function opens its own short-lived transactional session via
``session_scope``. Because the session factory uses ``expire_on_commit=False``,
the returned ORM objects remain usable (attributes loaded) after the session
closes — convenient for the UI and the service wrapper.
"""

from __future__ import annotations

import uuid
from typing import List, Optional, Union

from sqlalchemy import delete, func, select

from .connection import session_scope
from .models import BlogGeneration

IdType = Union[str, uuid.UUID]

# columns that update_generation is allowed to set
_UPDATABLE = {c.name for c in BlogGeneration.__table__.columns if c.name != "id"}


def _coerce_id(gen_id: IdType) -> uuid.UUID:
    if isinstance(gen_id, uuid.UUID):
        return gen_id
    return uuid.UUID(str(gen_id))


def create_generation(topic: str, *, status: str = "pending") -> BlogGeneration:
    """Insert a new generation row and return it (id + created_at populated)."""
    with session_scope() as session:
        gen = BlogGeneration(topic=topic, status=status)
        session.add(gen)
        session.flush()
        session.refresh(gen)
        return gen


def update_generation(gen_id: IdType, **fields) -> Optional[BlogGeneration]:
    """Update the given fields on a row. Returns the row, or None if missing.

    Raises ValueError for any field that is not a writable column.
    """
    unknown = set(fields) - _UPDATABLE
    if unknown:
        raise ValueError(f"Cannot update unknown column(s): {sorted(unknown)}")

    with session_scope() as session:
        gen = session.get(BlogGeneration, _coerce_id(gen_id))
        if gen is None:
            return None
        for key, value in fields.items():
            setattr(gen, key, value)
        session.flush()
        session.refresh(gen)
        return gen


def get_generation(gen_id: IdType) -> Optional[BlogGeneration]:
    with session_scope() as session:
        return session.get(BlogGeneration, _coerce_id(gen_id))


def list_generations(limit: int = 50, offset: int = 0) -> List[BlogGeneration]:
    """Return generations newest-first, paginated."""
    with session_scope() as session:
        stmt = (
            select(BlogGeneration)
            .order_by(BlogGeneration.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(session.scalars(stmt).all())


def delete_generation(gen_id: IdType) -> bool:
    """Delete a row. Returns True if it existed, False otherwise."""
    with session_scope() as session:
        gen = session.get(BlogGeneration, _coerce_id(gen_id))
        if gen is None:
            return False
        session.delete(gen)
        return True


def delete_all_generations() -> int:
    """Delete every generation row. Returns the number of rows removed."""
    with session_scope() as session:
        count = session.scalar(select(func.count()).select_from(BlogGeneration)) or 0
        session.execute(delete(BlogGeneration))
        return int(count)
