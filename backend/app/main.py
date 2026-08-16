from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from . import homework
from .classroom import ClassSection
from .config import settings
from .db import get_session, init_schema
from .schemas import (
    HomeworkCreate,
    HomeworkOut,
    PendingHomework,
    Student,
    StudentLookup,
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


@app.post("/api/students/homework", response_model=PendingHomework)
def pending_homework(
    lookup: StudentLookup, session: Session = Depends(get_session)
) -> PendingHomework:
    as_of = datetime.now(timezone.utc)
    rows = homework.pending_for(session, lookup.cohort(), as_of)
    return PendingHomework(
        student=Student(
            student_name=lookup.student_name,
            roll_no=lookup.roll_no,
            class_name=lookup.class_name,
            section=lookup.section,
        ),
        as_of=as_of,
        items=[HomeworkOut.model_validate(row) for row in rows],
    )


@app.post("/api/homework", response_model=HomeworkOut, status_code=201)
def set_homework(
    payload: HomeworkCreate, session: Session = Depends(get_session)
) -> HomeworkOut:
    return HomeworkOut.model_validate(homework.create(session, payload))


@app.get("/api/homework", response_model=list[HomeworkOut])
def homework_for_class(
    class_name: str = Query(alias="className", min_length=1),
    section: str = Query(min_length=1),
    session: Session = Depends(get_session),
) -> list[HomeworkOut]:
    cohort = ClassSection.parse(class_name, section)
    return [HomeworkOut.model_validate(r) for r in homework.set_for(session, cohort)]
