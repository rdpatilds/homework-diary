"""Runs against the real Postgres the app uses. `docker compose exec api python -m pytest`."""

from datetime import timedelta

import pytest
from sqlalchemy import delete

from app import accounts, staff
from app.accounts import Identity, Role, Username, now_utc
from app.db import SessionLocal, init_schema
from app.models import StaffAccount

SECRET = "a-test-secret-at-least-24-chars-long"
PREFIX = "pytest-"


@pytest.fixture()
def session():
    init_schema()
    with SessionLocal() as s:
        s.execute(delete(StaffAccount).where(StaffAccount.username.like(f"{PREFIX}%")))
        s.commit()
        yield s
        s.execute(delete(StaffAccount).where(StaffAccount.username.like(f"{PREFIX}%")))
        s.commit()


def make(session, name: str, password: str, role: Role = Role.TEACHER) -> StaffAccount:
    return accounts.create(
        session,
        username=Username.parse(f"{PREFIX}{name}"),
        password=password,
        display_name=name.title(),
        role=role,
    )


# ---------- usernames ----------


@pytest.mark.parametrize("raw", ["Iyer", " iyer ", "IYER", "iyer"])
def test_a_username_is_the_same_however_it_is_typed(raw: str):
    assert Username.parse(raw) == "iyer"


@pytest.mark.parametrize("raw", ["", "  ", "ab"])
def test_short_and_blank_usernames_are_rejected(raw: str):
    with pytest.raises(ValueError):
        Username.parse(raw)


# ---------- passwords ----------


def test_a_password_is_never_stored_in_the_clear():
    stored = accounts.hash_password("correct horse battery")

    assert "correct horse battery" not in stored
    assert stored.startswith("scrypt$")


def test_the_same_password_hashes_differently_every_time():
    assert accounts.hash_password("same") != accounts.hash_password("same")


def test_a_password_verifies_against_its_own_hash():
    stored = accounts.hash_password("correct horse battery")

    assert accounts.password_matches("correct horse battery", stored)
    assert not accounts.password_matches("wrong horse battery", stored)


@pytest.mark.parametrize("junk", ["", "nonsense", "scrypt$bad", "md5$1$2$3$4$5"])
def test_a_malformed_hash_never_matches(junk: str):
    assert not accounts.password_matches("anything", junk)


# ---------- signing in ----------


def test_the_right_password_signs_you_in(session):
    make(session, "iyer", "leaf-cross-section")

    who = accounts.authenticate(session, f"{PREFIX}iyer", "leaf-cross-section")

    assert who is not None
    assert who.role is Role.TEACHER


def test_the_wrong_password_does_not(session):
    make(session, "iyer", "leaf-cross-section")

    assert accounts.authenticate(session, f"{PREFIX}iyer", "guess") is None


def test_an_unknown_username_does_not(session):
    assert accounts.authenticate(session, f"{PREFIX}nobody", "guess") is None


def test_a_disabled_teacher_cannot_sign_in(session):
    make(session, "iyer", "leaf-cross-section")

    accounts.set_disabled(session, f"{PREFIX}iyer", True, now_utc())

    assert accounts.authenticate(session, f"{PREFIX}iyer", "leaf-cross-section") is None


def test_re_enabling_lets_them_back_in(session):
    make(session, "iyer", "leaf-cross-section")
    accounts.set_disabled(session, f"{PREFIX}iyer", True, now_utc())

    accounts.set_disabled(session, f"{PREFIX}iyer", False, now_utc())

    assert accounts.authenticate(session, f"{PREFIX}iyer", "leaf-cross-section")


def test_only_teachers_are_listed(session):
    make(session, "iyer", "password-one")
    make(session, "boss", "password-two", role=Role.ADMIN)

    names = [t.username for t in accounts.teachers(session)]

    assert f"{PREFIX}iyer" in names
    assert f"{PREFIX}boss" not in names


def test_an_admin_cannot_be_disabled_through_the_teacher_path(session):
    make(session, "boss", "password-two", role=Role.ADMIN)

    assert accounts.set_disabled(session, f"{PREFIX}boss", True, now_utc()) is None


# ---------- session tokens ----------


TEACHER = Identity("iyer", "Mrs Iyer", Role.TEACHER)
ADMIN = Identity("boss", "Administrator", Role.ADMIN)


def test_a_fresh_token_reads_back_as_the_same_person():
    now = now_utc()

    claim = staff.read(staff.mint(TEACHER, SECRET, now, timedelta(hours=1)), SECRET, now)

    assert claim is not None
    assert claim.username == "iyer"
    assert claim.role is Role.TEACHER


def test_the_role_survives_the_round_trip():
    now = now_utc()

    claim = staff.read(staff.mint(ADMIN, SECRET, now, timedelta(hours=1)), SECRET, now)

    assert claim is not None and claim.role is Role.ADMIN


def test_an_expired_token_is_refused():
    now = now_utc()
    token = staff.mint(TEACHER, SECRET, now, timedelta(hours=1))

    assert staff.read(token, SECRET, now + timedelta(hours=2)) is None


def test_a_token_signed_with_another_secret_is_refused():
    now = now_utc()
    token = staff.mint(TEACHER, SECRET, now, timedelta(hours=1))

    assert staff.read(token, SECRET + "x", now) is None


def test_a_tampered_payload_is_refused():
    now = now_utc()
    token = staff.mint(TEACHER, SECRET, now, timedelta(hours=1))
    payload, signature = token.split(".")
    forged = staff._b64(b"boss|admin|99999999999")

    assert staff.read(f"{forged}.{signature}", SECRET, now) is None
    assert payload != forged


@pytest.mark.parametrize("junk", ["", "nonsense", "a.b.c", "....", "!!!.???"])
def test_a_malformed_token_is_refused(junk: str):
    assert staff.read(junk, SECRET, now_utc()) is None


# ---------- bootstrap ----------


def test_the_first_admin_is_created_once(session):
    session.execute(delete(StaffAccount).where(StaffAccount.role == Role.ADMIN.value))
    session.commit()

    first = accounts.ensure_admin(session, f"{PREFIX}root", "bootstrap-password")
    second = accounts.ensure_admin(session, f"{PREFIX}root", "a-different-password")

    assert first is True
    assert second is False
    assert accounts.authenticate(session, f"{PREFIX}root", "bootstrap-password")


# ---------- throttle ----------


def test_the_throttle_locks_out_after_repeated_failures():
    now = now_utc()
    gate = staff.Throttle(limit=3)

    for _ in range(3):
        gate.record_failure("10.0.0.1", now)

    assert gate.locked_out("10.0.0.1", now)
    assert not gate.locked_out("10.0.0.2", now)


def test_the_throttle_forgets_once_the_window_passes():
    now = now_utc()
    gate = staff.Throttle(limit=3, window=timedelta(minutes=15))
    for _ in range(3):
        gate.record_failure("10.0.0.1", now)

    assert not gate.locked_out("10.0.0.1", now + timedelta(minutes=16))


def test_signing_in_clears_the_count():
    now = now_utc()
    gate = staff.Throttle(limit=3)
    for _ in range(2):
        gate.record_failure("10.0.0.1", now)

    gate.clear("10.0.0.1")

    assert not gate.locked_out("10.0.0.1", now)
