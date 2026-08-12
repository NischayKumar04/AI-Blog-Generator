"""Shared pytest fixtures.

The ``db`` fixture points ``DATABASE_URL`` at a fresh SQLite file inside the
test's tmp directory, resets the cached engine, and creates the schema. No
Postgres server (and no API keys) are required for the default suite.
"""

from __future__ import annotations

import pytest

from db import connection


@pytest.fixture()
def db(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file.as_posix()}")
    connection.reset_engine()
    connection.init_db()
    yield
    connection.reset_engine()
