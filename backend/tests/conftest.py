"""Points the suite at its own database before the app is imported.

These tests delete rows, including every admin, to check the bootstrap. Against
the working database that wipes real accounts, so the suite gets its own and the
two never touch. This must run before `app.config` reads the environment, which
is why it lives in conftest rather than a fixture."""

import os

from sqlalchemy import create_engine, text

TEST_DB = "schoolapp_test"


def _use_test_database() -> None:
    working_url = os.environ.get("DATABASE_URL")
    if not working_url:
        raise RuntimeError("DATABASE_URL is not set")
    if working_url.rsplit("/", 1)[-1] == TEST_DB:
        return

    engine = create_engine(working_url, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": TEST_DB}
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{TEST_DB}"'))
    engine.dispose()

    os.environ["DATABASE_URL"] = f"{working_url.rsplit('/', 1)[0]}/{TEST_DB}"


_use_test_database()
