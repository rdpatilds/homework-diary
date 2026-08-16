"""Runs against the real Postgres the app uses. `docker compose exec api python -m pytest`."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import delete

from app import homework
from app.classroom import ClassSection
from app.db import SessionLocal, init_schema
from app.models import Homework

COHORT = ClassSection.parse("TEST-99", "Z")
OTHER = ClassSection.parse("TEST-99", "Y")


@pytest.fixture()
def session():
    init_schema()
    with SessionLocal() as s:
        s.execute(delete(Homework).where(Homework.class_name == COHORT.class_name))
        s.commit()
        yield s
        s.execute(delete(Homework).where(Homework.class_name == COHORT.class_name))
        s.commit()


def add(session, cohort: ClassSection, title: str, days: float) -> None:
    session.add(
        Homework(
            title=title,
            subject="Test",
            details="",
            class_name=cohort.class_name,
            section=cohort.section,
            due_at=datetime.now(timezone.utc) + timedelta(days=days),
            assigned_by="Fixture",
        )
    )
    session.commit()


def test_only_future_deadlines_are_pending(session):
    add(session, COHORT, "already closed", -3)
    add(session, COHORT, "still open", 3)

    titles = [h.title for h in homework.pending_for(session, COHORT, datetime.now(timezone.utc))]

    assert titles == ["still open"]


def test_pending_is_soonest_first(session):
    add(session, COHORT, "third", 9)
    add(session, COHORT, "first", 1)
    add(session, COHORT, "second", 4)

    titles = [h.title for h in homework.pending_for(session, COHORT, datetime.now(timezone.utc))]

    assert titles == ["first", "second", "third"]


def test_a_section_never_sees_another_sections_work(session):
    add(session, COHORT, "for Z", 2)
    add(session, OTHER, "for Y", 2)

    titles = [h.title for h in homework.pending_for(session, COHORT, datetime.now(timezone.utc))]

    assert titles == ["for Z"]


def test_set_for_includes_closed_work(session):
    add(session, COHORT, "already closed", -3)
    add(session, COHORT, "still open", 3)

    titles = {h.title for h in homework.set_for(session, COHORT)}

    assert titles == {"already closed", "still open"}
