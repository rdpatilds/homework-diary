from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from .classroom import ClassSection
from .models import Homework
from .schemas import HomeworkCreate


def create(session: Session, payload: HomeworkCreate) -> Homework:
    cohort = payload.cohort()
    row = Homework(
        title=payload.title,
        subject=payload.subject,
        details=payload.details,
        class_name=cohort.class_name,
        section=cohort.section,
        due_at=payload.due_at,
        assigned_by=payload.assigned_by,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def pending_for(
    session: Session, cohort: ClassSection, as_of: datetime
) -> list[Homework]:
    """Homework set for this cohort whose deadline has not passed, soonest first."""
    stmt = (
        select(Homework)
        .where(
            Homework.class_name == cohort.class_name,
            Homework.section == cohort.section,
            Homework.due_at > as_of,
        )
        .order_by(Homework.due_at.asc())
    )
    return list(session.scalars(stmt))


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
