"""Runs against the real Postgres the app uses. `docker compose exec api python -m pytest`."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import delete, select

from app import homework
from app.classroom import ClassSection, StudentKey
from app.homework import Done, Missed, Open
from app.models import Homework, Submission

from app.db import SessionLocal, init_schema

COHORT = ClassSection.parse("TEST-99", "Z")
PRIYA = StudentKey.parse("TEST-99", "Z", "24")
ARUN = StudentKey.parse("TEST-99", "Z", "25")
OTHER_SECTION = StudentKey.parse("TEST-99", "Y", "24")


def now() -> datetime:
    return datetime.now(timezone.utc)


@pytest.fixture()
def session():
    init_schema()
    with SessionLocal() as s:
        s.execute(delete(Homework).where(Homework.class_name == COHORT.class_name))
        s.commit()
        yield s
        s.execute(delete(Homework).where(Homework.class_name == COHORT.class_name))
        s.commit()


def add(session, title: str, days: float, cohort: ClassSection = COHORT) -> Homework:
    row = Homework(
        title=title,
        subject="Test",
        details="",
        class_name=cohort.class_name,
        section=cohort.section,
        due_at=now() + timedelta(days=days),
        assigned_by="Fixture",
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def states(session, student: StudentKey) -> dict[str, object]:
    return {
        a.homework.title: type(a.status)
        for a in homework.diary_for(session, student, now())
    }


def test_untouched_future_work_is_open(session):
    add(session, "still open", 3)

    assert states(session, PRIYA) == {"still open": Open}


def test_untouched_past_work_is_missed(session):
    add(session, "never handed in", -3)

    assert states(session, PRIYA) == {"never handed in": Missed}


def test_handing_in_makes_it_done(session):
    row = add(session, "essay", 3)

    homework.hand_in(session, PRIYA, row.id, now())

    assert states(session, PRIYA) == {"essay": Done}


def test_taking_it_back_makes_it_open_again(session):
    row = add(session, "essay", 3)
    homework.hand_in(session, PRIYA, row.id, now())

    homework.take_back(session, PRIYA, row.id, now())

    assert states(session, PRIYA) == {"essay": Open}


def test_work_that_is_done_and_past_its_deadline_is_settled(session):
    row = add(session, "handed in on time", -3)

    homework.hand_in(session, PRIYA, row.id, now())

    assert states(session, PRIYA) == {}


def test_one_students_submission_does_not_touch_another(session):
    row = add(session, "essay", 3)

    homework.hand_in(session, PRIYA, row.id, now())

    assert states(session, PRIYA) == {"essay": Done}
    assert states(session, ARUN) == {"essay": Open}


def test_handing_in_twice_changes_nothing(session):
    row = add(session, "essay", 3)

    first = homework.hand_in(session, PRIYA, row.id, now())
    second = homework.hand_in(session, PRIYA, row.id, now())

    assert first is not None and second is not None
    assert first.submitted_at == second.submitted_at
    assert session.scalar(select(Submission).where(Submission.homework_id == row.id))
    assert len(session.scalars(select(Submission).where(Submission.homework_id == row.id)).all()) == 1


def test_taking_back_twice_changes_nothing(session):
    row = add(session, "essay", 3)
    homework.hand_in(session, PRIYA, row.id, now())

    homework.take_back(session, PRIYA, row.id, now())
    again = homework.take_back(session, PRIYA, row.id, now())

    assert again is not None
    assert isinstance(again.status, Open)


def test_a_student_cannot_hand_in_another_sections_work(session):
    row = add(session, "for Z", 3)

    assert homework.hand_in(session, OTHER_SECTION, row.id, now()) is None


def test_unknown_homework_is_refused(session):
    assert homework.hand_in(session, PRIYA, 99_999_999, now()) is None


def test_the_diary_is_soonest_first(session):
    add(session, "third", 9)
    add(session, "first", -1)
    add(session, "second", 4)

    titles = [a.homework.title for a in homework.diary_for(session, PRIYA, now())]

    assert titles == ["first", "second", "third"]


def test_set_for_ignores_submissions(session):
    row = add(session, "handed in on time", -3)
    homework.hand_in(session, PRIYA, row.id, now())

    assert [h.title for h in homework.set_for(session, COHORT)] == ["handed in on time"]
