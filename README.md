# Homework Diary

A homework tracker for one school. Students enter their details on the landing
page and see every assignment still open for their class. Teachers set homework
against a class, a section, and a deadline.

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
that a student finds their work despite messy casing, and that another section
cannot see it. The pytest suite covers the pending query against the real
database.

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
  classroom.py   ClassSection: the cohort value, and the one normalisation rule
  schemas.py     request and response models, all validation
  homework.py    the queries
  models.py      the table
  main.py        routes, thin
frontend/src
  api/           fetch wrapper and DTO types
  deadline.ts    countdown and timezone conversion, pure
  pages/         StudentPage, TeacherPage
```

**Cohorts are normalised once.** `ClassSection.parse` trims, collapses inner
whitespace, and uppercases. A student typing `8` / `a` and a teacher typing
` 8 ` / `A` land on the same cohort. Everything downstream compares stored,
normalised values.

**Pending means the deadline has not passed.** There is no per-student
submission record, so nothing tracks whether an individual handed work in. See
"Known limits".

**Deadlines are UTC.** The database column is `timestamptz`. The browser
converts its `datetime-local` value with `toISOString()` before sending. A naive
datetime posted directly to the API is read as UTC.

## Known limits

- No authentication. Anyone who reaches `/teacher` can set homework, and any
  name and roll number opens a diary. Add auth before this leaves the school
  network.
- No submission tracking. "Pending" is derived from the deadline, not from
  whether a given student has handed the work in. Adding a `submission` table
  keyed by homework and roll number is the natural next step, and is what makes
  roll number load-bearing rather than decorative.
- No teacher edit or delete. Homework can only be created.
- Schema is created at startup with `create_all`. One table, no migration tool.
  Introduce Alembic before the second schema change.
