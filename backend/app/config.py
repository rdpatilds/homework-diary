import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    cors_origins: tuple[str, ...]

    @classmethod
    def from_env(cls) -> "Settings":
        url = os.environ.get("DATABASE_URL")
        if not url:
            raise RuntimeError("DATABASE_URL is not set")
        origins = os.environ.get("CORS_ORIGINS", "http://localhost:5173")
        return cls(
            database_url=url,
            cors_origins=tuple(o.strip() for o in origins.split(",") if o.strip()),
        )


settings = Settings.from_env()
