"""Staff accounts. Admins create teachers; both sign in the same way.

Passwords are stored as scrypt hashes with a per-password salt, never in the
clear and never recoverable. scrypt is memory hard and lives in the standard
library, so this needs no dependency."""

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import StaffAccount

# Roughly 100ms per hash on a modern core. Raise N, never lower it.
_N, _R, _P, _LEN = 2**14, 8, 1, 32


class Role(str, Enum):
    ADMIN = "admin"
    TEACHER = "teacher"


class Username:
    """Usernames are compared, so they normalise once. Same rule as the
    classroom identifiers, for the same reason."""

    @staticmethod
    def parse(raw: str) -> str:
        name = " ".join(raw.split()).lower()
        if not name:
            raise ValueError("Username is required")
        if len(name) < 3:
            raise ValueError("Username must be at least 3 characters")
        if " " in name:
            raise ValueError("Username cannot contain spaces")
        return name


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=_LEN
    )
    return f"scrypt${_N}${_R}${_P}${salt.hex()}${digest.hex()}"


def password_matches(password: str, stored: str) -> bool:
    """Constant time, and false rather than throwing on anything malformed."""
    try:
        scheme, n, r, p, salt_hex, digest_hex = stored.split("$")
        if scheme != "scrypt":
            return False
        candidate = hashlib.scrypt(
            password.encode(),
            salt=bytes.fromhex(salt_hex),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(digest_hex) // 2,
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(candidate.hex(), digest_hex)


@dataclass(frozen=True, slots=True)
class Identity:
    """Who is signed in, as the rest of the app needs to know them."""

    username: str
    display_name: str
    role: Role

    @property
    def is_admin(self) -> bool:
        return self.role is Role.ADMIN


def identify(row: StaffAccount) -> Identity:
    return Identity(row.username, row.display_name, Role(row.role))


def credential_stamp(row: StaffAccount) -> str:
    """A short fingerprint of the stored hash, carried inside the session token.

    Changing a password changes the hash, so every token minted under the old
    one stops matching and those sessions end. That is what makes a password
    change kick out whoever else was holding a session. It is a digest of a
    digest, so it gives nothing away about the password."""
    return hashlib.sha256(row.password_hash.encode()).hexdigest()[:12]


def find(session: Session, username: str) -> StaffAccount | None:
    return session.scalar(
        select(StaffAccount).where(StaffAccount.username == username)
    )


def authenticate(session: Session, username: str, password: str) -> StaffAccount | None:
    """The account row, so the caller can take both an identity and a credential
    stamp from it. None covers unknown, disabled and wrong password alike, so
    nothing about which one it was leaks back."""
    row = find(session, username)
    if row is None:
        # Spend the same time as a real check so absence is not timeable.
        hash_password(password)
        return None
    if row.disabled_at is not None:
        return None
    if not password_matches(password, row.password_hash):
        return None
    return row


def create(
    session: Session,
    *,
    username: str,
    password: str,
    display_name: str,
    role: Role,
) -> StaffAccount:
    row = StaffAccount(
        username=username,
        password_hash=hash_password(password),
        display_name=display_name,
        role=role.value,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


class WrongPassword(Exception):
    """The current password did not match, so nothing was changed."""


class SamePassword(Exception):
    """The new password is the old one."""


def change_password(
    session: Session, username: str, current: str, new: str
) -> StaffAccount:
    """Self service. Proves you know the current password first, so a stolen
    session alone cannot take an account over."""
    row = find(session, username)
    if row is None or row.disabled_at is not None:
        raise WrongPassword
    if not password_matches(current, row.password_hash):
        raise WrongPassword
    if password_matches(new, row.password_hash):
        raise SamePassword
    row.password_hash = hash_password(new)
    session.commit()
    session.refresh(row)
    return row


def reset_password(session: Session, username: str, new: str) -> StaffAccount | None:
    """Admin path, for a teacher who has forgotten theirs. No current password,
    because the admin cannot know it. Ends that teacher's sessions."""
    row = find(session, username)
    if row is None or row.role != Role.TEACHER.value:
        return None
    row.password_hash = hash_password(new)
    session.commit()
    session.refresh(row)
    return row


def teachers(session: Session) -> list[StaffAccount]:
    stmt = (
        select(StaffAccount)
        .where(StaffAccount.role == Role.TEACHER.value)
        .order_by(StaffAccount.username.asc())
    )
    return list(session.scalars(stmt))


def set_disabled(
    session: Session, username: str, disabled: bool, now: datetime
) -> StaffAccount | None:
    row = find(session, username)
    if row is None or row.role != Role.TEACHER.value:
        return None
    row.disabled_at = now if disabled else None
    session.commit()
    session.refresh(row)
    return row


def ensure_admin(session: Session, username: str, password: str) -> bool:
    """Bootstrap. Creates the first admin if there is none, and does nothing on
    every run after that. Never rewrites an existing password."""
    existing = session.scalar(
        select(StaffAccount).where(StaffAccount.role == Role.ADMIN.value)
    )
    if existing is not None:
        return False
    create(
        session,
        username=Username.parse(username),
        password=password,
        display_name="Administrator",
        role=Role.ADMIN,
    )
    return True


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
