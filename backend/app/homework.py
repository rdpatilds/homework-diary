from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import and_, delete, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from .classroom import ClassSection, StudentKey
from .models import Homework, Submission


@dataclass(frozen=True, slots=True)
class Open:
    pass


@dataclass(frozen=True, slots=True)
class Missed:
    pass


@dataclass(frozen=True, slots=True)
class Done:
    submitted_at: datetime


Status = Open | Missed | Done


@dataclass(frozen=True, slots=True)
class Assignment:
    """One piece of homework as it stands for one student. Status is derived
    from the submission and the clock, so a done assignment always has a time
    and an open one never does."""

    homework: Homework
    as_of: datetime
    submitted_at: datetime | None

    @property
    def status(self) -> Status:
        if self.submitted_at is not None:
            return Done(self.submitted_at)
        return Open() if self.homework.due_at > self.as_of else Missed()


def create(
    session: Session,
    *,
    cohort: ClassSection,
    title: str,
    subject: str,
    details: str,
    assigned_by: str,
    due_at: datetime,
) -> Homework:
    row = Homework(
        title=title,
        subject=subject,
        details=details,
        class_name=cohort.class_name,
        section=cohort.section,
        due_at=due_at,
        assigned_by=assigned_by,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def diary_for(
    session: Session, student: StudentKey, as_of: datetime
) -> list[Assignment]:
    """What the student still owes, plus what they have handed in while the
    deadline is still open so they can undo a mistake. Work that is both past
    its deadline and handed in is settled, and is left out."""
    stmt = (
        select(Homework, Submission.submitted_at)
        .outerjoin(
            Submission,
            and_(
                Submission.homework_id == Homework.id,
                Submission.roll_no == student.roll_no,
            ),
        )
        .where(
            Homework.class_name == student.cohort.class_name,
            Homework.section == student.cohort.section,
            or_(Homework.due_at > as_of, Submission.submitted_at.is_(None)),
        )
        .order_by(Homework.due_at.asc())
    )
    return [
        Assignment(homework, as_of, submitted_at)
        for homework, submitted_at in session.execute(stmt)
    ]


def _owned_by(session: Session, homework_id: int, student: StudentKey) -> Homework | None:
    """A student may only touch homework set for their own cohort."""
    row = session.get(Homework, homework_id)
    if row is None:
        return None
    if (row.class_name, row.section) != (student.cohort.class_name, student.cohort.section):
        return None
    return row


def hand_in(
    session: Session, student: StudentKey, homework_id: int, as_of: datetime
) -> Assignment | None:
    row = _owned_by(session, homework_id, student)
    if row is None:
        return None
    session.execute(
        insert(Submission)
        .values(homework_id=row.id, roll_no=student.roll_no)
        .on_conflict_do_nothing(constraint="uq_submission_homework_roll")
    )
    session.commit()
    submitted_at = session.scalar(
        select(Submission.submitted_at).where(
            Submission.homework_id == row.id, Submission.roll_no == student.roll_no
        )
    )
    return Assignment(row, as_of, submitted_at)


def take_back(
    session: Session, student: StudentKey, homework_id: int, as_of: datetime
) -> Assignment | None:
    row = _owned_by(session, homework_id, student)
    if row is None:
        return None
    session.execute(
        delete(Submission).where(
            Submission.homework_id == row.id, Submission.roll_no == student.roll_no
        )
    )
    session.commit()
    return Assignment(row, as_of, None)


def set_for(session: Session, cohort: ClassSection) -> list[Homework]:
    """Everything ever set for this cohort, newest deadline first."""
    stmt = (
        select(Homework)
        .where(
            Homework.class_name == cohort.class_name,
            Homework.section == cohort.section,
        )
        .order_by(Homework.due_at.desc())
    )
    return list(session.scalars(stmt))
