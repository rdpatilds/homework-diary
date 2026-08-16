"""Fills an empty homework table with a week of realistic work, including one
item already past its deadline so the missed state is visible. Safe to re-run:
it does nothing once any homework exists."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from .db import SessionLocal, init_schema
from .models import Homework

SAMPLES = [
    ("Algebra worksheet", "Maths", "Both sides, show your working.", "8", "A", -2, "Mr Banerjee"),
    ("Photosynthesis lab write-up", "Science", "Draw the leaf cross-section, label the chloroplasts, and write up what changed in the starch test.", "8", "A", 2, "Mrs Iyer"),
    ("Chapter 6, sums 1-20", "Maths", "Show every step. Questions 17 to 20 are the stretch set.", "8", "A", 5, "Mr Banerjee"),
    ("Letter to the editor", "English", "250 words on the new library hours. Formal register.", "8", "A", 9, "Ms Fernandes"),
    ("Map of the Deccan plateau", "Geography", "Mark the four rivers and shade the basalt region.", "8", "B", 3, "Mrs Iyer"),
    ("Trigonometry worksheet", "Maths", "Both sides. Calculator allowed for the last four.", "10", "A", 4, "Mr Banerjee"),
]


def run() -> int:
    init_schema()
    with SessionLocal() as session:
        if session.scalar(select(func.count()).select_from(Homework)):
            return 0
        now = datetime.now(timezone.utc)
        session.add_all(
            Homework(
                title=title,
                subject=subject,
                details=details,
                class_name=class_name,
                section=section,
                due_at=now + timedelta(days=days, hours=6),
                assigned_by=teacher,
            )
            for title, subject, details, class_name, section, days, teacher in SAMPLES
        )
        session.commit()
        return len(SAMPLES)


if __name__ == "__main__":
    print(f"seeded {run()} rows")
