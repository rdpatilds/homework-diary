from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

from .classroom import ClassSection


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


class StudentLookup(CohortFields):
    student_name: str = Field(min_length=1, max_length=120)
    roll_no: str = Field(min_length=1, max_length=20)

    @field_validator("student_name", "roll_no", mode="after")
    @classmethod
    def _trim(cls, value: str) -> str:
        trimmed = " ".join(value.split())
        if not trimmed:
            raise ValueError("This field is required")
        return trimmed


class HomeworkCreate(CohortFields):
    title: str = Field(min_length=1, max_length=200)
    subject: str = Field(min_length=1, max_length=80)
    details: str = Field(default="", max_length=4000)
    assigned_by: str = Field(min_length=1, max_length=120)
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


class PendingHomework(Payload):
    student: Student
    as_of: datetime
    items: list[HomeworkOut]
