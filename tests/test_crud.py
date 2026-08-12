"""CRUD tests — hermetic, SQLite-backed, no API keys."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from db import crud


def test_create_generation_populates_id_and_defaults(db):
    gen = crud.create_generation("My Topic")
    assert isinstance(gen.id, uuid.UUID)
    assert gen.topic == "My Topic"
    assert gen.status == "pending"
    assert gen.created_at is not None


def test_get_generation_roundtrip(db):
    gen = crud.create_generation("T")
    fetched = crud.get_generation(gen.id)
    assert fetched is not None
    assert fetched.id == gen.id
    # id also accepted as a string
    assert crud.get_generation(str(gen.id)) is not None


def test_get_missing_returns_none(db):
    assert crud.get_generation(uuid.uuid4()) is None


def test_update_generation_sets_fields(db):
    gen = crud.create_generation("T")
    updated = crud.update_generation(
        gen.id,
        status="completed",
        blog_title="Hello",
        word_count=123,
        plan_json={"blog_title": "Hello", "tasks": []},
    )
    assert updated.status == "completed"
    assert updated.blog_title == "Hello"
    assert updated.word_count == 123
    assert updated.plan_json == {"blog_title": "Hello", "tasks": []}


def test_update_missing_returns_none(db):
    assert crud.update_generation(uuid.uuid4(), status="completed") is None


def test_update_unknown_column_raises(db):
    gen = crud.create_generation("T")
    with pytest.raises(ValueError):
        crud.update_generation(gen.id, not_a_real_column="x")


def test_list_generations_newest_first(db):
    g1 = crud.create_generation("first")
    g2 = crud.create_generation("second")
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    crud.update_generation(g1.id, created_at=base)
    crud.update_generation(g2.id, created_at=base + timedelta(hours=1))

    rows = crud.list_generations()
    assert [r.topic for r in rows] == ["second", "first"]


def test_list_pagination(db):
    for i in range(5):
        crud.create_generation(f"topic-{i}")
    page = crud.list_generations(limit=2, offset=0)
    assert len(page) == 2
    assert len(crud.list_generations(limit=2, offset=4)) == 1


def test_delete_generation(db):
    gen = crud.create_generation("T")
    assert crud.delete_generation(gen.id) is True
    assert crud.get_generation(gen.id) is None
    # deleting again reports False
    assert crud.delete_generation(gen.id) is False
