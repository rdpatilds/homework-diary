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

# Somebody other than any account under test, so the "not yourself" guard only
# fires in the tests that mean to trigger it.
ACTOR = Identity(f"{PREFIX}actor", "Actor", Role.ADMIN)


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

    row = accounts.authenticate(session, f"{PREFIX}iyer", "leaf-cross-section")

    assert row is not None
    assert accounts.identify(row).role is Role.TEACHER


def test_the_wrong_password_does_not(session):
    make(session, "iyer", "leaf-cross-section")

    assert accounts.authenticate(session, f"{PREFIX}iyer", "guess") is None


def test_an_unknown_username_does_not(session):
    assert accounts.authenticate(session, f"{PREFIX}nobody", "guess") is None


def test_a_disabled_teacher_cannot_sign_in(session):
    make(session, "iyer", "leaf-cross-section")

    accounts.set_disabled(session, ACTOR, f"{PREFIX}iyer", True, now_utc())

    assert accounts.authenticate(session, f"{PREFIX}iyer", "leaf-cross-section") is None


def test_re_enabling_lets_them_back_in(session):
    make(session, "iyer", "leaf-cross-section")
    accounts.set_disabled(session, ACTOR, f"{PREFIX}iyer", True, now_utc())

    accounts.set_disabled(session, ACTOR, f"{PREFIX}iyer", False, now_utc())

    assert accounts.authenticate(session, f"{PREFIX}iyer", "leaf-cross-section")


def test_admins_and_teachers_are_listed_together(session):
    make(session, "iyer", "password-one")
    make(session, "boss", "password-two", role=Role.ADMIN)

    names = [t.username for t in accounts.everyone(session)]

    assert f"{PREFIX}iyer" in names
    assert f"{PREFIX}boss" in names


def test_admins_come_before_teachers(session):
    make(session, "iyer", "password-one")
    make(session, "boss", "password-two", role=Role.ADMIN)

    roles = [t.role for t in accounts.everyone(session) if t.username.startswith(PREFIX)]

    assert roles == sorted(roles)
    assert roles[0] == Role.ADMIN.value


# ---------- guards against locking everyone out ----------


def only_admin(session, name: str) -> StaffAccount:
    """Clears the field so this account really is the last active admin."""
    session.execute(delete(StaffAccount).where(StaffAccount.role == Role.ADMIN.value))
    session.commit()
    return make(session, name, "password-two", role=Role.ADMIN)


def test_an_admin_can_be_disabled_when_another_remains(session):
    only_admin(session, "boss")
    make(session, "deputy", "password-three", role=Role.ADMIN)

    row = accounts.set_disabled(session, ACTOR, f"{PREFIX}deputy", True, now_utc())

    assert row is not None and row.disabled_at is not None


def test_the_last_active_admin_cannot_be_disabled(session):
    only_admin(session, "boss")

    with pytest.raises(accounts.LastAdmin):
        accounts.set_disabled(session, ACTOR, f"{PREFIX}boss", True, now_utc())

    assert accounts.find(session, f"{PREFIX}boss").disabled_at is None


def test_an_already_disabled_admin_does_not_count_as_active(session):
    only_admin(session, "boss")
    make(session, "deputy", "password-three", role=Role.ADMIN)
    accounts.set_disabled(session, ACTOR, f"{PREFIX}deputy", True, now_utc())

    with pytest.raises(accounts.LastAdmin):
        accounts.set_disabled(session, ACTOR, f"{PREFIX}boss", True, now_utc())


def test_you_cannot_disable_yourself(session):
    make(session, "boss", "password-two", role=Role.ADMIN)
    make(session, "deputy", "password-three", role=Role.ADMIN)
    self_acting = Identity(f"{PREFIX}boss", "Boss", Role.ADMIN)

    with pytest.raises(accounts.NotYourself):
        accounts.set_disabled(session, self_acting, f"{PREFIX}boss", True, now_utc())


def test_you_may_still_re_enable_yourself(session):
    """Re-enabling locks nobody out, so it needs no guard."""
    make(session, "boss", "password-two", role=Role.ADMIN)
    self_acting = Identity(f"{PREFIX}boss", "Boss", Role.ADMIN)

    row = accounts.set_disabled(session, self_acting, f"{PREFIX}boss", False, now_utc())

    assert row is not None and row.disabled_at is None


def test_the_last_admin_rule_ignores_teachers(session):
    only_admin(session, "boss")
    make(session, "iyer", "password-one")

    row = accounts.set_disabled(session, ACTOR, f"{PREFIX}iyer", True, now_utc())

    assert row is not None and row.disabled_at is not None


# ---------- changing a password ----------


def test_changing_a_password_lets_the_new_one_in(session):
    make(session, "iyer", "leaf-cross-section")

    accounts.change_password(session, f"{PREFIX}iyer", "leaf-cross-section", "stomata-2026")

    assert accounts.authenticate(session, f"{PREFIX}iyer", "stomata-2026")
    assert accounts.authenticate(session, f"{PREFIX}iyer", "leaf-cross-section") is None


def test_the_current_password_must_be_right(session):
    row = make(session, "iyer", "leaf-cross-section")
    before = row.password_hash

    with pytest.raises(accounts.WrongPassword):
        accounts.change_password(session, f"{PREFIX}iyer", "guess", "stomata-2026")

    assert accounts.find(session, f"{PREFIX}iyer").password_hash == before


def test_the_new_password_must_be_different(session):
    make(session, "iyer", "leaf-cross-section")

    with pytest.raises(accounts.SamePassword):
        accounts.change_password(
            session, f"{PREFIX}iyer", "leaf-cross-section", "leaf-cross-section"
        )


def test_a_disabled_account_cannot_change_its_password(session):
    make(session, "iyer", "leaf-cross-section")
    accounts.set_disabled(session, ACTOR, f"{PREFIX}iyer", True, now_utc())

    with pytest.raises(accounts.WrongPassword):
        accounts.change_password(
            session, f"{PREFIX}iyer", "leaf-cross-section", "stomata-2026"
        )


def test_an_admin_can_reset_a_teacher_without_the_old_password(session):
    make(session, "iyer", "leaf-cross-section")

    accounts.reset_password(session, ACTOR, f"{PREFIX}iyer", "issued-by-the-office")

    assert accounts.authenticate(session, f"{PREFIX}iyer", "issued-by-the-office")


def test_an_admin_can_reset_another_admin(session):
    make(session, "boss", "password-two", role=Role.ADMIN)

    accounts.reset_password(session, ACTOR, f"{PREFIX}boss", "issued-by-the-office")

    assert accounts.authenticate(session, f"{PREFIX}boss", "issued-by-the-office")


def test_you_cannot_reset_your_own_password_this_way(session):
    """That path skips the current-password check, so it stays on /account."""
    make(session, "boss", "password-two", role=Role.ADMIN)
    self_acting = Identity(f"{PREFIX}boss", "Boss", Role.ADMIN)

    with pytest.raises(accounts.NotYourself):
        accounts.reset_password(session, self_acting, f"{PREFIX}boss", "sneaky-change")

    assert accounts.authenticate(session, f"{PREFIX}boss", "password-two")


def test_resetting_an_unknown_account_returns_nothing(session):
    assert accounts.reset_password(session, ACTOR, f"{PREFIX}ghost", "new-password") is None


# ---------- session tokens ----------


TEACHER = Identity("iyer", "Mrs Iyer", Role.TEACHER)
ADMIN = Identity("boss", "Administrator", Role.ADMIN)
STAMP = "abc123def456"


def test_a_fresh_token_reads_back_as_the_same_person():
    now = now_utc()

    claim = staff.read(
        staff.mint(TEACHER, STAMP, SECRET, now, timedelta(hours=1)), SECRET, now
    )

    assert claim is not None
    assert claim.username == "iyer"
    assert claim.role is Role.TEACHER
    assert claim.stamp == STAMP


def test_the_role_survives_the_round_trip():
    now = now_utc()

    claim = staff.read(
        staff.mint(ADMIN, STAMP, SECRET, now, timedelta(hours=1)), SECRET, now
    )

    assert claim is not None and claim.role is Role.ADMIN


def test_an_expired_token_is_refused():
    now = now_utc()
    token = staff.mint(TEACHER, STAMP, SECRET, now, timedelta(hours=1))

    assert staff.read(token, SECRET, now + timedelta(hours=2)) is None


def test_a_token_signed_with_another_secret_is_refused():
    now = now_utc()
    token = staff.mint(TEACHER, STAMP, SECRET, now, timedelta(hours=1))

    assert staff.read(token, SECRET + "x", now) is None


def test_a_tampered_payload_is_refused():
    now = now_utc()
    token = staff.mint(TEACHER, STAMP, SECRET, now, timedelta(hours=1))
    payload, signature = token.split(".")
    forged = staff._b64(b"boss|admin|abc123def456|99999999999")

    assert staff.read(f"{forged}.{signature}", SECRET, now) is None
    assert payload != forged


# ---------- the stamp is what ends other sessions ----------


def test_the_stamp_changes_when_the_password_changes(session):
    row = make(session, "iyer", "leaf-cross-section")
    before = accounts.credential_stamp(row)

    changed = accounts.change_password(
        session, f"{PREFIX}iyer", "leaf-cross-section", "stomata-2026"
    )

    assert accounts.credential_stamp(changed) != before


def test_the_stamp_changes_when_an_admin_resets_it(session):
    row = make(session, "iyer", "leaf-cross-section")
    before = accounts.credential_stamp(row)

    reset = accounts.reset_password(session, ACTOR, f"{PREFIX}iyer", "issued-by-the-office")

    assert reset is not None
    assert accounts.credential_stamp(reset) != before


def test_the_stamp_is_steady_while_the_password_is(session):
    row = make(session, "iyer", "leaf-cross-section")

    accounts.set_disabled(session, ACTOR, f"{PREFIX}iyer", True, now_utc())
    accounts.set_disabled(session, ACTOR, f"{PREFIX}iyer", False, now_utc())

    assert accounts.credential_stamp(
        accounts.find(session, f"{PREFIX}iyer")
    ) == accounts.credential_stamp(row)


def test_the_stamp_gives_nothing_away_about_the_password(session):
    row = make(session, "iyer", "leaf-cross-section")

    stamp = accounts.credential_stamp(row)

    assert "leaf-cross-section" not in stamp
    assert stamp not in row.password_hash


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
