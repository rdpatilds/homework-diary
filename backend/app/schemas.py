from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

from .classroom import ClassSection, StudentKey
from .homework import Assignment, Done, Missed, Open


class Payload(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, from_attributes=True
    )


def _as_utc(value: datetime) -> datetime:
    """A naive datetime from a direct API caller is read as UTC. The browser
    always sends an explicit offset."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class CohortFields(Payload):
    class_name: str = Field(min_length=1, max_length=40)
    section: str = Field(min_length=1, max_length=40)

    @field_validator("class_name", "section", mode="after")
    @classmethod
    def _tidy(cls, value: str) -> str:
        return " ".join(value.split()).upper()

    def cohort(self) -> ClassSection:
        return ClassSection.parse(self.class_name, self.section)


class StudentRef(CohortFields):
    """Enough to identify whose submission this is. The teacher surfaces never
    need it, so it stays off the homework payloads."""

    roll_no: str = Field(min_length=1, max_length=20)

    @field_validator("roll_no", mode="after")
    @classmethod
    def _tidy_roll(cls, value: str) -> str:
        return " ".join(value.split()).upper()

    def student(self) -> StudentKey:
        return StudentKey.parse(self.class_name, self.section, self.roll_no)


class StudentLookup(StudentRef):
    student_name: str = Field(min_length=1, max_length=120)

    @field_validator("student_name", mode="after")
    @classmethod
    def _trim(cls, value: str) -> str:
        trimmed = " ".join(value.split())
        if not trimmed:
            raise ValueError("This field is required")
        return trimmed


class HomeworkCreate(CohortFields):
    """No assigned_by. Whoever is signed in owns the work, so a client cannot
    put someone else's name on it."""

    title: str = Field(min_length=1, max_length=200)
    subject: str = Field(min_length=1, max_length=80)
    details: str = Field(default="", max_length=4000)
    due_at: datetime

    @field_validator("due_at", mode="after")
    @classmethod
    def _future_utc(cls, value: datetime) -> datetime:
        due = _as_utc(value)
        if due <= datetime.now(timezone.utc):
            raise ValueError("The deadline must be in the future")
        return due


class HomeworkOut(Payload):
    id: int
    title: str
    subject: str
    details: str
    class_name: str
    section: str
    due_at: datetime
    assigned_by: str


class Student(Payload):
    student_name: str
    roll_no: str
    class_name: str
    section: str


class OpenStatus(Payload):
    state: Literal["open"]


class MissedStatus(Payload):
    state: Literal["missed"]


class DoneStatus(Payload):
    state: Literal["done"]
    submitted_at: datetime


AssignmentStatus = Annotated[
    OpenStatus | MissedStatus | DoneStatus, Field(discriminator="state")
]


class AssignmentOut(Payload):
    """Homework as it stands for one student. There is no `done` flag beside a
    nullable timestamp, so the two cannot disagree."""

    id: int
    title: str
    subject: str
    details: str
    class_name: str
    section: str
    due_at: datetime
    assigned_by: str
    status: AssignmentStatus

    @classmethod
    def of(cls, assignment: Assignment) -> "AssignmentOut":
        match assignment.status:
            case Done(submitted_at=at):
                status: AssignmentStatus = DoneStatus(state="done", submitted_at=at)
            case Missed():
                status = MissedStatus(state="missed")
            case Open():
                status = OpenStatus(state="open")
        row = assignment.homework
        return cls(
            id=row.id,
            title=row.title,
            subject=row.subject,
            details=row.details,
            class_name=row.class_name,
            section=row.section,
            due_at=row.due_at,
            assigned_by=row.assigned_by,
            status=status,
        )


class StudentDiary(Payload):
    student: Student
    as_of: datetime
    assignments: list[AssignmentOut]


class SignIn(Payload):
    username: str = Field(min_length=1, max_length=60)
    password: str = Field(min_length=1, max_length=200)


class StaffSession(Payload):
    """What the browser is told about itself. Never carries the token."""

    signed_in: bool
    username: str | None = None
    display_name: str | None = None
    role: Literal["admin", "teacher"] | None = None


class NewTeacher(Payload):
    username: str = Field(min_length=3, max_length=60)
    password: str = Field(min_length=8, max_length=200)
    display_name: str = Field(min_length=1, max_length=120)

    @field_validator("display_name", mode="after")
    @classmethod
    def _trim_name(cls, value: str) -> str:
        trimmed = " ".join(value.split())
        if not trimmed:
            raise ValueError("A name is required")
        return trimmed


class TeacherOut(Payload):
    username: str
    display_name: str
    created_at: datetime
    disabled_at: datetime | None
