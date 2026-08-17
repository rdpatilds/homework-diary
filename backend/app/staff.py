"""Signed session tokens and a sign-in throttle.

A token carries the username, the role and its own expiry, signed with the
server secret. Nothing is stored server side, so rotating SESSION_SECRET
invalidates every session at once."""

import base64
import hashlib
import hmac
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .accounts import Identity, Role

_DOMAIN = b"schoolapp/staff-session/v2"


def _key(secret: str) -> bytes:
    return hashlib.sha256(_DOMAIN + b"\x00" + secret.encode()).digest()


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def mint(
    identity: Identity, stamp: str, secret: str, now: datetime, ttl: timedelta
) -> str:
    expires_at = int((now + ttl).timestamp())
    payload = (
        f"{identity.username}|{identity.role.value}|{stamp}|{expires_at}".encode()
    )
    signature = hmac.new(_key(secret), payload, hashlib.sha256).digest()
    return f"{_b64(payload)}.{_b64(signature)}"


@dataclass(frozen=True, slots=True)
class Claim:
    username: str
    role: Role
    # Fingerprint of the password hash this token was minted against. The
    # caller compares it with the account's current one.
    stamp: str


def read(token: str, secret: str, now: datetime) -> Claim | None:
    """None for anything tampered with, malformed or expired. The caller never
    has to tell those apart."""
    parts = token.split(".")
    if len(parts) != 2:
        return None
    try:
        payload = _unb64(parts[0])
        signature = _unb64(parts[1])
    except (ValueError, base64.binascii.Error):
        return None

    expected = hmac.new(_key(secret), payload, hashlib.sha256).digest()
    if not hmac.compare_digest(signature, expected):
        return None

    try:
        username, role, stamp, expires_at = payload.decode().split("|")
        if now.timestamp() >= int(expires_at):
            return None
        return Claim(username, Role(role), stamp)
    except ValueError:
        return None


@dataclass
class Throttle:
    """Slows down password guessing. Per process and in memory, so it is a speed
    bump rather than a wall. See the readme."""

    limit: int = 8
    window: timedelta = timedelta(minutes=15)
    _failures: dict[str, list[float]] = field(default_factory=dict)

    def _recent(self, who: str, now: datetime) -> list[float]:
        cutoff = (now - self.window).timestamp()
        recent = [t for t in self._failures.get(who, []) if t > cutoff]
        if recent:
            self._failures[who] = recent
        else:
            self._failures.pop(who, None)
        return recent

    def locked_out(self, who: str, now: datetime) -> bool:
        return len(self._recent(who, now)) >= self.limit

    def record_failure(self, who: str, now: datetime) -> None:
        self._recent(who, now)
        self._failures.setdefault(who, []).append(now.timestamp())

    def clear(self, who: str) -> None:
        self._failures.pop(who, None)
