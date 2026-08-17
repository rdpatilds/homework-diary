from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from . import accounts, homework, staff
from .accounts import Identity, Role, Username
from .classroom import ClassSection
from .config import settings
from .db import SessionLocal, get_session, init_schema
from .schemas import (
    AssignmentOut,
    ChangePassword,
    HomeworkCreate,
    HomeworkOut,
    NewStaff,
    ResetPassword,
    SignIn,
    StaffMember,
    StaffSession,
    Student,
    StudentDiary,
    StudentLookup,
    StudentRef,
)

COOKIE = "staff_session"


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_schema()
    with SessionLocal() as session:
        if accounts.ensure_admin(
            session, settings.admin_username, settings.admin_password
        ):
            print(f"created the first admin account: {settings.admin_username}")
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


throttle = staff.Throttle()


def _caller(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _whoami(request: Request, session: Session) -> Identity | None:
    """The cookie says who you claim to be. The account row decides whether that
    still holds, so disabling a teacher ends their session on the next call."""
    token = request.cookies.get(COOKIE, "")
    if not token:
        return None
    claim = staff.read(token, settings.session_secret, datetime.now(timezone.utc))
    if claim is None:
        return None
    row = accounts.find(session, claim.username)
    if row is None or row.disabled_at is not None or row.role != claim.role.value:
        return None
    # Minted against a password that has since changed, so this session is over.
    if claim.stamp != accounts.credential_stamp(row):
        return None
    return accounts.identify(row)


def _issue_cookie(response: Response, row, now: datetime) -> None:
    response.set_cookie(
        COOKIE,
        staff.mint(
            accounts.identify(row),
            accounts.credential_stamp(row),
            settings.session_secret,
            now,
            timedelta(hours=settings.session_hours),
        ),
        max_age=settings.session_hours * 3600,
        httponly=True,
        samesite="strict",
        secure=settings.cookie_secure,
        path="/",
    )


def signed_in(
    request: Request, session: Session = Depends(get_session)
) -> Identity:
    who = _whoami(request, session)
    if who is None:
        raise HTTPException(401, "Sign in first")
    return who


def admin_only(who: Identity = Depends(signed_in)) -> Identity:
    if not who.is_admin:
        raise HTTPException(403, "Only an administrator can manage teachers")
    return who


def _as_session(who: Identity | None) -> StaffSession:
    if who is None:
        return StaffSession(signed_in=False)
    return StaffSession(
        signed_in=True,
        username=who.username,
        display_name=who.display_name,
        role=who.role.value,
    )


@app.get("/api/staff/session", response_model=StaffSession)
def staff_session(
    request: Request, session: Session = Depends(get_session)
) -> StaffSession:
    return _as_session(_whoami(request, session))


@app.post("/api/staff/session", response_model=StaffSession)
def sign_in_route(
    payload: SignIn,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
) -> StaffSession:
    now = datetime.now(timezone.utc)
    where = _caller(request)

    if throttle.locked_out(where, now):
        raise HTTPException(429, "Too many attempts. Wait a few minutes and try again.")

    try:
        username = Username.parse(payload.username)
    except ValueError:
        username = ""

    row = (
        accounts.authenticate(session, username, payload.password) if username else None
    )
    if row is None:
        throttle.record_failure(where, now)
        raise HTTPException(401, "That username and password do not match.")

    throttle.clear(where)
    _issue_cookie(response, row, now)
    return _as_session(accounts.identify(row))


@app.delete("/api/staff/session", response_model=StaffSession)
def sign_out(response: Response) -> StaffSession:
    response.delete_cookie(COOKIE, path="/", httponly=True, samesite="strict")
    return StaffSession(signed_in=False)


@app.post("/api/staff/password", response_model=StaffSession)
def change_password(
    payload: ChangePassword,
    request: Request,
    response: Response,
    who: Identity = Depends(signed_in),
    session: Session = Depends(get_session),
) -> StaffSession:
    now = datetime.now(timezone.utc)
    where = f"password:{who.username}:{_caller(request)}"

    if throttle.locked_out(where, now):
        raise HTTPException(429, "Too many attempts. Wait a few minutes and try again.")

    try:
        row = accounts.change_password(
            session, who.username, payload.current_password, payload.new_password
        )
    except accounts.WrongPassword:
        throttle.record_failure(where, now)
        raise HTTPException(401, "Your current password is not right.")
    except accounts.SamePassword:
        raise HTTPException(422, "The new password is the one you already have.")

    throttle.clear(where)
    # The change ended every session for this account, including this one.
    # Hand back a fresh cookie so the person who made the change stays put.
    _issue_cookie(response, row, now)
    return _as_session(accounts.identify(row))


@app.post("/api/admin/staff/{username}/password", response_model=StaffMember)
def reset_staff_password(
    username: str,
    payload: ResetPassword,
    who: Identity = Depends(admin_only),
    session: Session = Depends(get_session),
) -> StaffMember:
    try:
        row = accounts.reset_password(
            session, who, Username.parse(username), payload.password
        )
    except accounts.NotYourself:
        raise HTTPException(
            409, "Change your own password on the account page, where it asks for the current one."
        )
    if row is None:
        raise HTTPException(404, "No such account")
    return StaffMember.model_validate(row)


@app.get("/api/admin/staff", response_model=list[StaffMember])
def list_staff(
    _: Identity = Depends(admin_only), session: Session = Depends(get_session)
) -> list[StaffMember]:
    return [StaffMember.model_validate(s) for s in accounts.everyone(session)]


@app.post("/api/admin/staff", response_model=StaffMember, status_code=201)
def add_staff(
    payload: NewStaff,
    _: Identity = Depends(admin_only),
    session: Session = Depends(get_session),
) -> StaffMember:
    username = Username.parse(payload.username)
    if accounts.find(session, username) is not None:
        raise HTTPException(409, f"The username {username} is already taken")
    row = accounts.create(
        session,
        username=username,
        password=payload.password,
        display_name=payload.display_name,
        role=Role(payload.role),
    )
    return StaffMember.model_validate(row)


@app.post("/api/admin/staff/{username}/disabled", response_model=StaffMember)
def set_staff_disabled(
    username: str,
    disabled: bool = Query(...),
    who: Identity = Depends(admin_only),
    session: Session = Depends(get_session),
) -> StaffMember:
    try:
        row = accounts.set_disabled(
            session, who, Username.parse(username), disabled, datetime.now(timezone.utc)
        )
    except accounts.NotYourself:
        raise HTTPException(409, "You cannot disable your own account.")
    except accounts.LastAdmin:
        raise HTTPException(
            409, "This is the only active administrator. Add another one first."
        )
    if row is None:
        raise HTTPException(404, "No such account")
    return StaffMember.model_validate(row)


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
    payload: HomeworkCreate,
    who: Identity = Depends(signed_in),
    session: Session = Depends(get_session),
) -> HomeworkOut:
    row = homework.create(
        session,
        cohort=payload.cohort(),
        title=payload.title,
        subject=payload.subject,
        details=payload.details,
        # Whoever is signed in owns the work. A client cannot claim to be
        # someone else by editing the payload.
        assigned_by=who.display_name,
        due_at=payload.due_at,
    )
    return HomeworkOut.model_validate(row)


@app.get("/api/homework", response_model=list[HomeworkOut])
def homework_for_class(
    class_name: str = Query(alias="className", min_length=1),
    section: str = Query(min_length=1),
    _: Identity = Depends(signed_in),
    session: Session = Depends(get_session),
) -> list[HomeworkOut]:
    cohort = ClassSection.parse(class_name, section)
    return [HomeworkOut.model_validate(r) for r in homework.set_for(session, cohort)]
