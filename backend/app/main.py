from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from . import homework
from .classroom import ClassSection
from .config import settings
from .db import get_session, init_schema
from .schemas import (
    AssignmentOut,
    HomeworkCreate,
    HomeworkOut,
    Student,
    StudentDiary,
    StudentLookup,
    StudentRef,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_schema()
    yield


app = FastAPI(title="School Homework Diary", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ValueError)
async def _bad_input(_: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/students/diary", response_model=StudentDiary)
def student_diary(
    lookup: StudentLookup, session: Session = Depends(get_session)
) -> StudentDiary:
    as_of = datetime.now(timezone.utc)
    assignments = homework.diary_for(session, lookup.student(), as_of)
    return StudentDiary(
        student=Student(
            student_name=lookup.student_name,
            roll_no=lookup.roll_no,
            class_name=lookup.class_name,
            section=lookup.section,
        ),
        as_of=as_of,
        assignments=[AssignmentOut.of(a) for a in assignments],
    )


@app.post("/api/homework/{homework_id}/submission", response_model=AssignmentOut)
def hand_in(
    homework_id: int, who: StudentRef, session: Session = Depends(get_session)
) -> AssignmentOut:
    as_of = datetime.now(timezone.utc)
    result = homework.hand_in(session, who.student(), homework_id, as_of)
    if result is None:
        raise HTTPException(404, "No such homework for that class")
    return AssignmentOut.of(result)


@app.delete("/api/homework/{homework_id}/submission", response_model=AssignmentOut)
def take_back(
    homework_id: int, who: StudentRef, session: Session = Depends(get_session)
) -> AssignmentOut:
    as_of = datetime.now(timezone.utc)
    result = homework.take_back(session, who.student(), homework_id, as_of)
    if result is None:
        raise HTTPException(404, "No such homework for that class")
    return AssignmentOut.of(result)


@app.post("/api/homework", response_model=HomeworkOut, status_code=201)
def set_homework(
    payload: HomeworkCreate, session: Session = Depends(get_session)
) -> HomeworkOut:
    row = homework.create(
        session,
        cohort=payload.cohort(),
        title=payload.title,
        subject=payload.subject,
        details=payload.details,
        assigned_by=payload.assigned_by,
        due_at=payload.due_at,
    )
    return HomeworkOut.model_validate(row)


@app.get("/api/homework", response_model=list[HomeworkOut])
def homework_for_class(
    class_name: str = Query(alias="className", min_length=1),
    section: str = Query(min_length=1),
    session: Session = Depends(get_session),
) -> list[HomeworkOut]:
    cohort = ClassSection.parse(class_name, section)
    return [HomeworkOut.model_validate(r) for r in homework.set_for(session, cohort)]
