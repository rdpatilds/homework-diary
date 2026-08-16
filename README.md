# Homework Diary

A homework tracker for one school. Students enter their details on the landing
page and see what they still owe, mark work as handed in, and undo that if they
tap it by mistake. Teachers set homework against a class, a section, and a
deadline.

- Frontend: React 18, TypeScript, Vite, served by nginx.
- Backend: FastAPI, SQLAlchemy 2, Pydantic v2, Python 3.12.
- Storage: PostgreSQL 16, as a Docker image.

## Run it

```
docker compose up -d --build
docker compose exec api python -m app.seed   # optional sample homework
```

| Surface | URL |
| --- | --- |
| Student landing page | http://localhost:8080 |
| Teacher page | http://localhost:8080/teacher |
| API docs | http://localhost:8000/docs |
| Postgres | localhost:55432, user/password/db all `schoolapp` |

The seed is safe to re-run. It does nothing once any homework exists.

## Verify it

`verify.py` drives the running API end to end. It needs no dependencies beyond a
local Python.

```
python verify.py
docker compose exec api python -m pytest tests -q
```

`verify.py` proves a teacher can set homework, that a past deadline is refused,
that a student finds their work despite messy casing, that handing in and taking
back move it between states and are both idempotent, and that one student's
submission leaves their classmate's diary alone. Pass `http://localhost:8080` to
run the same checks through nginx. The pytest suite covers the diary query and
the submission rules against the real database.

## Develop

The frontend proxies `/api` to `localhost:8000`, so the same relative paths work
in development and behind nginx.

```
docker compose up -d db api
cd frontend && npm install && npm run dev     # http://localhost:5173
```

Typecheck with `npm run typecheck`.

## How it is put together

```
backend/app
  classroom.py   ClassSection and StudentKey, and the one normalisation rule
  schemas.py     request and response models, all validation
  homework.py    the diary query, the submission rules, Assignment
  models.py      the two tables
  main.py        routes, thin
frontend/src
  api/           fetch wrapper and DTO types
  deadline.ts    countdown and timezone conversion, pure
  pages/         StudentPage, TeacherPage
```

**Identities are normalised once.** `ClassSection.parse` and `StudentKey.parse`
trim, collapse inner whitespace, and uppercase. A student typing `8` / `a` /
` 24 ` and a teacher typing ` 8 ` / `A` land on the same cohort and the same
student. Building a `StudentKey` is the only way to reach a normalised roll
number, so no query can be handed a raw string.

**Pending means not handed in.** A `submission` row means one student handed one
piece of homework in. Absence means they have not. There is no status column, so
nothing can fall out of step with the facts.

**An assignment's state is derived, never stored.** `Assignment.status` reads
`submitted_at` and the clock and returns `Open`, `Missed`, or `Done`. Only
`Done` carries a time, so a completed assignment without a timestamp cannot be
represented on either side of the wire.

| State | Deadline | Handed in |
| --- | --- | --- |
| Open | Ahead | No |
| Done | Ahead | Yes |
| Missed | Passed | No |

Work that is both past its deadline and handed in is settled, and the diary
leaves it out.

**Handing in is idempotent.** A unique constraint on `(homework_id, roll_no)`
plus `ON CONFLICT DO NOTHING` means a double tap or a retried request converges
on the same single row. Taking it back is a delete, so it converges too. A
student can only touch homework set for their own cohort.

**Deadlines are UTC.** The database column is `timestamptz`. The browser
converts its `datetime-local` value with `toISOString()` before sending. A naive
datetime posted directly to the API is read as UTC.

## Known limits

- No authentication, and this now matters more than it did. Any roll number
  opens that student's diary and can mark their work handed in. Anyone who
  reaches `/teacher` can set homework. Add auth before this leaves the school
  network.
- No roster, so a roll number is whatever the student types. `07` and `7` are
  two different students on purpose, because merging them would let one student
  see another's submissions if a school ever used both. The fix is a roster the
  school owns, not cleverer string handling.
- Students mark their own work handed in. Nothing verifies it, and a teacher
  cannot see who has. A teacher-facing submission list is the obvious next
  addition and needs no schema change.
- Handing in work after its deadline settles it, so it leaves the diary on the
  next visit and the undo goes with it.
- No teacher edit or delete. Homework can only be created.
- Schema is created at startup with `create_all`. Two tables, no migration tool.
  Introduce Alembic before the next schema change.
