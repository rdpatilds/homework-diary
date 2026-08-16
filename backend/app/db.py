import time

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from .config import settings
from .models import Base

engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)


def get_session():
    with SessionLocal() as session:
        yield session


def init_schema(attempts: int = 30, delay_seconds: float = 1.0) -> None:
    last: Exception | None = None
    for _ in range(attempts):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            Base.metadata.create_all(engine)
            return
        except OperationalError as exc:
            last = exc
            time.sleep(delay_seconds)
    raise RuntimeError(f"Database never became reachable: {last}")
