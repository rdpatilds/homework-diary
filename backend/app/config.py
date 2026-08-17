import os
from dataclasses import dataclass

MIN_SECRET = 24
MIN_PASSWORD = 8


def _require(name: str, minimum: int) -> str:
    value = os.environ.get(name, "")
    if len(value) < minimum:
        raise RuntimeError(
            f"{name} must be set and at least {minimum} characters. "
            "Put one in .env; see .env.example."
        )
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    cors_origins: tuple[str, ...]
    session_secret: str
    admin_username: str
    admin_password: str
    cookie_secure: bool
    session_hours: int

    @classmethod
    def from_env(cls) -> "Settings":
        url = os.environ.get("DATABASE_URL")
        if not url:
            raise RuntimeError("DATABASE_URL is not set")

        origins = os.environ.get("CORS_ORIGINS", "http://localhost:5173")
        return cls(
            database_url=url,
            cors_origins=tuple(o.strip() for o in origins.split(",") if o.strip()),
            # Fail at startup rather than serve staff routes with a guessable key.
            session_secret=_require("SESSION_SECRET", MIN_SECRET),
            admin_username=os.environ.get("ADMIN_USERNAME", "admin"),
            admin_password=_require("ADMIN_PASSWORD", MIN_PASSWORD),
            cookie_secure=os.environ.get("COOKIE_SECURE", "").lower()
            in {"1", "true", "yes"},
            session_hours=int(os.environ.get("SESSION_HOURS", "12")),
        )


settings = Settings.from_env()
