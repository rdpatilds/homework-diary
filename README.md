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
cp .env.example .env      # then put real values in it
docker compose up -d --build
docker compose exec api python -m app.seed   # optional sample homework
```

Compose refuses to start without `SESSION_SECRET` and `ADMIN_PASSWORD`, so
there is no way to bring this up with a default password. On the first run
against an empty database the API creates one administrator from those values
and logs the username. It never touches that account again, so changing
`ADMIN_PASSWORD` later does nothing.

| Surface | URL | Sign-in |
| --- | --- | --- |
| Student landing page | http://localhost:8080 | None |
| Teacher page | http://localhost:8080/teacher | Any staff account |
| Admin page | http://localhost:8080/admin | Administrator only |
| Change your password | http://localhost:8080/account | Any staff account |
| API docs | http://localhost:8000/docs | |
| Postgres | localhost:55432 | user/password/db all `schoolapp` |

The seed is safe to re-run. It does nothing once any homework exists.

## Verify it

`verify.py` drives the running API end to end. It needs no dependencies beyond a
local Python.

```
python verify.py
docker compose exec api python -m pytest tests -q
```

`verify.py` runs 63 checks with a separate cookie jar per role and per device. It
proves the staff API is shut to anonymous callers, that an admin can create a
teacher and a teacher cannot, that work is credited to whoever signed in, that
students need no sign-in, that disabling a teacher ends the session they already
hold, and that changing a password ends every other session but not the one that
made the change. Pass `http://localhost:8080` to run the same checks through nginx.

The pytest suite runs against its own database, `schoolapp_test`, created on
first use. It deletes rows freely, including every admin, so it must never point
at the working database. `backend/tests/conftest.py` enforces that.

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
  accounts.py    staff accounts, password hashing, roles
  staff.py       signed session tokens and the sign-in throttle
  schemas.py     request and response models, all validation
  homework.py    the diary query, the submission rules, Assignment
  models.py      the three tables
  main.py        routes, thin
frontend/src
  api/           fetch wrapper and DTO types
  deadline.ts    countdown and timezone conversion, pure
  components/    StaffGate wraps both staff pages
  pages/         StudentPage, TeacherPage, AdminPage
```

## Who can do what

| | Students | Teachers | Admin |
| --- | --- | --- | --- |
| See a class diary, hand work in | Yes | | |
| Set homework, list a class | | Yes | Yes |
| Create and disable accounts, including other admins | | | Yes |

**The gate is on the API, not the page.** Hiding a React route protects nothing,
so every staff route depends on a signed-in identity and answers 401 or 403 to
anyone else. `verify.py` calls each one anonymously to prove it.

**Passwords are hashed with scrypt**, a fresh 16-byte salt each, stored as
`scrypt$N$r$p$salt$hash`. Nobody can read a password back, including the admin
who set it. An unknown username still pays the cost of a hash, so absence is not
timeable.

**A session is a signed cookie**, HttpOnly and SameSite=Strict, carrying only a
username, a role and an expiry. Nothing is stored server side, so rotating
`SESSION_SECRET` signs everyone out at once. Every request re-reads the account
behind the cookie, which is why disabling a teacher ends the session they are
already holding rather than waiting for it to expire.

**Homework is credited to whoever is signed in.** `assignedBy` is not a field a
client can send, so nobody can put another teacher's name on their work.

## Passwords

Anyone signed in changes their own at `/account`, proving the current one first
so a stolen session alone cannot take an account over. An admin issues a new one
to a teacher who has forgotten theirs, from the row on `/admin`.

**Changing a password ends every other session for that account.** The token
carries a short fingerprint of the stored hash, and every request compares it
with the account's current one. A new password means a new hash, so tokens
minted under the old one stop matching. Whoever made the change is handed a
fresh cookie so they stay put; everyone else is signed out at once. An admin
reset does the same to that teacher.

The admin who bootstrapped from `ADMIN_PASSWORD` should change it at `/account`
on first sign-in. After that the value in `.env` is inert, because the bootstrap
only runs when there is no admin at all. If that password is ever lost, delete
the admin row and restart the API to bootstrap a fresh one.

## Guards against locking yourself out

An admin creates other admins, so the obvious next question is what stops the
school losing every way in. Three rules, all enforced on the server:

- **You cannot disable your own account.** It would take effect on your next
  request, which is the one that reloads the page.
- **You cannot disable the last active administrator.** Add another first. The
  admin page says so in the panel header while only one is active, and greys the
  button out rather than letting you find out by failing.
- **You cannot reset your own password from the admin page.** That path skips
  the current-password check, so it stays on `/account` where the check happens.
  One admin resetting *another* is allowed, and ends that admin's sessions.

Re-enabling is never blocked, because it locks nobody out.

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

- Students still do not sign in. Any roll number opens that student's diary and
  can mark their work handed in. That is deliberate for now, and it is the
  remaining hole.
- The sign-in throttle counts failures per IP in memory. It resets on restart
  and does not span replicas, so it slows guessing rather than stopping it. Put
  a real rate limit at the proxy before this faces the internet.
- No self-service reset. A teacher who forgets their password needs an admin to
  issue a new one, and an admin who forgets theirs needs database access. There
  is no email on file to send a link to.
- `COOKIE_SECURE` is false by default so it works over plain HTTP locally. Set
  it to true the moment this is behind TLS, or session cookies travel in clear.
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
