"""End-to-end check against a running stack.

Proves that the staff API is shut to anonymous callers, that an admin can create
a teacher, that the teacher can then set work, that a student sees it and can
hand it in, and that disabling the teacher ends their access. Run it after
`docker compose up -d`.

    python verify.py [base-url]     (default http://localhost:8000)

Point it at http://localhost:8080 to check the same paths through nginx.
Reads ADMIN_USERNAME and ADMIN_PASSWORD from .env.
"""

import http.cookiejar
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
CLASS, SECTION = "VERIFY-7", "Q"
PRIYA = {"className": CLASS, "section": SECTION, "rollNo": "24"}
ARUN = {"className": CLASS, "section": SECTION, "rollNo": "25"}
OUTSIDER = {"className": CLASS, "section": "R", "rollNo": "24"}
TEACHER_USER = "verify-teacher"
TEACHER_PASS = "verify-teacher-password"
failures: list[str] = []


def from_env_file() -> dict[str, str]:
    found: dict[str, str] = {}
    path = Path(__file__).with_name(".env")
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                found[key.strip()] = value.strip()
    return found


ENV = from_env_file()
ADMIN_USER = os.environ.get("ADMIN_USERNAME") or ENV.get("ADMIN_USERNAME", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASSWORD") or ENV.get("ADMIN_PASSWORD", "")


class Caller:
    """One browser. Its own cookie jar, so sessions never bleed between roles."""

    def __init__(self, name: str):
        self.name = name
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
        )

    def __call__(self, method: str, path: str, body: dict | None = None):
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(
            f"{BASE}{path}", data=data, method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with self.opener.open(request, timeout=20) as response:
                return response.status, json.loads(response.read() or b"null")
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read() or b"null")


anon = Caller("anonymous")
admin = Caller("admin")
teacher = Caller("teacher")


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{'' if ok else f'  <- {detail}'}")
    if not ok:
        failures.append(name)


def diary(who: dict, caller: Caller = anon):
    return caller("POST", "/api/students/diary", {"studentName": "Verify Student", **who})


def state_of(body, homework_id: int):
    if not isinstance(body, dict):
        return None
    for item in body["assignments"]:
        if item["id"] == homework_id:
            return item["status"]["state"]
    return None


print(f"Verifying {BASE}\n")

status, body = anon("GET", "/api/health")
check("api is up", status == 200 and body == {"status": "ok"}, f"{status} {body}")

if not ADMIN_PASS:
    print("\nFAILED: no ADMIN_PASSWORD in .env or the environment.")
    sys.exit(1)

print("\n-- the staff api is shut to anonymous callers --")

due = (datetime.now(timezone.utc) + timedelta(days=4)).isoformat()
homework_body = {
    "title": "Verify run: tectonic plates poster", "subject": "Geography",
    "details": "Trace the ring of fire.", "className": CLASS, "section": SECTION,
    "dueAt": due,
}

status, body = anon("POST", "/api/homework", homework_body)
check("anonymous cannot set homework", status == 401, f"{status} {body}")

status, body = anon("GET", f"/api/homework?className={CLASS}&section={SECTION}")
check("anonymous cannot list a class", status == 401, f"{status} {body}")

status, body = anon("GET", "/api/admin/teachers")
check("anonymous cannot list teachers", status == 401, f"{status} {body}")

status, body = anon("POST", "/api/staff/session", {"username": ADMIN_USER, "password": "wrong"})
check("a wrong password is refused", status == 401, f"{status} {body}")

status, body = anon("GET", "/api/staff/session")
check("anonymous reports signed out",
      status == 200 and body.get("signedIn") is False, f"{status} {body}")

print("\n-- the admin signs in and creates a teacher --")

status, body = admin("POST", "/api/staff/session", {"username": ADMIN_USER, "password": ADMIN_PASS})
check("the admin can sign in",
      status == 200 and body.get("role") == "admin", f"{status} {body}")

admin("POST", f"/api/admin/teachers/{TEACHER_USER}/disabled?disabled=false")
status, body = admin("POST", "/api/admin/teachers", {
    "username": TEACHER_USER, "password": TEACHER_PASS, "displayName": "Verify Teacher",
})
check("the admin can create a teacher", status in (201, 409), f"{status} {body}")

status, body = admin("POST", "/api/admin/teachers", {
    "username": TEACHER_USER, "password": TEACHER_PASS, "displayName": "Verify Teacher",
})
check("the same username cannot be taken twice", status == 409, f"{status} {body}")

status, body = admin("POST", "/api/admin/teachers", {
    "username": "shorty", "password": "short", "displayName": "Too Short",
})
check("a short password is refused", status == 422, f"{status} {body}")

status, body = admin("GET", "/api/admin/teachers")
listed = [t["username"] for t in body] if status == 200 else []
check("the new teacher is listed", TEACHER_USER in listed, f"{status} {body}")

print("\n-- the teacher signs in and sets work --")

status, body = teacher("POST", "/api/staff/session", {"username": TEACHER_USER, "password": TEACHER_PASS})
check("the teacher can sign in",
      status == 200 and body.get("role") == "teacher", f"{status} {body}")

status, body = teacher("GET", "/api/admin/teachers")
check("a teacher cannot manage teachers", status == 403, f"{status} {body}")

status, created = teacher("POST", "/api/homework", homework_body)
check("the teacher can set homework", status == 201, f"{status} {created}")
hw = created["id"] if isinstance(created, dict) and "id" in created else -1

check("the work is credited to whoever signed in",
      isinstance(created, dict) and created.get("assignedBy") == "Verify Teacher",
      f"{created}")

status, body = teacher("POST", "/api/homework", {
    **homework_body, "title": "Deadline already gone",
    "dueAt": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
})
check("a deadline in the past is refused", status == 422, f"{status} {body}")

print("\n-- students need no sign-in and see the right work --")

status, body = diary({"className": f"  {CLASS.lower()} ",
                      "section": f" {SECTION.lower()} ", "rollNo": " 24 "})
check("a student sees it without signing in",
      status == 200 and state_of(body, hw) == "open", f"{status} {body}")

status, body = diary(OUTSIDER)
check("another section does not see it",
      status == 200 and state_of(body, hw) is None, f"{status} {body}")

status, first = anon("POST", f"/api/homework/{hw}/submission", PRIYA)
check("handing it in marks it done",
      status == 200 and isinstance(first, dict)
      and first["status"]["state"] == "done", f"{status} {first}")

status, again = anon("POST", f"/api/homework/{hw}/submission", PRIYA)
check("handing it in twice is the same as once",
      status == 200 and isinstance(again, dict)
      and again["status"] == first["status"], f"{status} {again}")

status, body = diary(ARUN)
check("a classmate still owes it", state_of(body, hw) == "open", f"{status} {body}")

status, body = anon("POST", f"/api/homework/{hw}/submission", OUTSIDER)
check("another section cannot hand it in", status == 404, f"{status} {body}")

status, body = anon("DELETE", f"/api/homework/{hw}/submission", PRIYA)
check("taking it back makes it pending again",
      status == 200 and isinstance(body, dict)
      and body["status"]["state"] == "open", f"{status} {body}")

status, body = diary({"className": CLASS, "section": SECTION, "rollNo": "  "})
check("a blank roll number is refused", status == 422, f"{status} {body}")

print("\n-- disabling a teacher ends their access --")

status, body = admin("POST", f"/api/admin/teachers/{TEACHER_USER}/disabled?disabled=true")
check("the admin can disable a teacher",
      status == 200 and body.get("disabledAt") is not None, f"{status} {body}")

status, body = teacher("POST", "/api/homework", homework_body)
check("their existing session stops working", status == 401, f"{status} {body}")

blocked = Caller("blocked")
status, body = blocked("POST", "/api/staff/session",
                       {"username": TEACHER_USER, "password": TEACHER_PASS})
check("they cannot sign in again", status == 401, f"{status} {body}")

status, body = admin("POST", f"/api/admin/teachers/{TEACHER_USER}/disabled?disabled=false")
check("re-enabling them works", status == 200 and body.get("disabledAt") is None,
      f"{status} {body}")

status, body = blocked("POST", "/api/staff/session",
                       {"username": TEACHER_USER, "password": TEACHER_PASS})
check("and they can sign back in", status == 200, f"{status} {body}")

print("\n-- changing a password --")

NEW_PASS = "verify-teacher-new-password"
desk = Caller("teacher-desk")
phone = Caller("teacher-phone")

for caller in (desk, phone):
    caller("POST", "/api/staff/session",
           {"username": TEACHER_USER, "password": TEACHER_PASS})

status, body = desk("POST", "/api/staff/password",
                    {"currentPassword": "not-it", "newPassword": NEW_PASS})
check("a wrong current password is refused", status == 401, f"{status} {body}")

status, body = desk("POST", "/api/staff/password",
                    {"currentPassword": TEACHER_PASS, "newPassword": TEACHER_PASS})
check("the new password must differ from the old", status == 422, f"{status} {body}")

status, body = desk("POST", "/api/staff/password",
                    {"currentPassword": TEACHER_PASS, "newPassword": "short"})
check("a short new password is refused", status == 422, f"{status} {body}")

status, body = desk("POST", "/api/staff/password",
                    {"currentPassword": TEACHER_PASS, "newPassword": NEW_PASS})
check("the password changes", status == 200 and body.get("signedIn") is True,
      f"{status} {body}")

status, body = desk("GET", "/api/homework?className=" + CLASS + "&section=" + SECTION)
check("whoever changed it stays signed in", status == 200, f"{status} {body}")

status, body = phone("GET", "/api/homework?className=" + CLASS + "&section=" + SECTION)
check("every other session is ended", status == 401, f"{status} {body}")

stale = Caller("stale")
status, body = stale("POST", "/api/staff/session",
                     {"username": TEACHER_USER, "password": TEACHER_PASS})
check("the old password no longer works", status == 401, f"{status} {body}")

status, body = stale("POST", "/api/staff/session",
                     {"username": TEACHER_USER, "password": NEW_PASS})
check("the new password does", status == 200, f"{status} {body}")

print("\n-- an admin resets a forgotten password --")

status, body = admin("POST", f"/api/admin/teachers/{TEACHER_USER}/password",
                     {"password": TEACHER_PASS})
check("the admin can reset a teacher", status == 200, f"{status} {body}")

status, body = stale("GET", f"/api/homework?className={CLASS}&section={SECTION}")
check("the reset ends that teacher's session", status == 401, f"{status} {body}")

status, body = stale("POST", "/api/staff/session",
                     {"username": TEACHER_USER, "password": TEACHER_PASS})
check("they sign in with what the admin issued", status == 200, f"{status} {body}")

status, body = desk("POST", f"/api/admin/teachers/{TEACHER_USER}/password",
                    {"password": "teacher-should-not-reach-this"})
check("a teacher cannot reset anyone", status in (401, 403), f"{status} {body}")

status, body = admin("POST", f"/api/admin/teachers/{ADMIN_USER}/password",
                     {"password": "admins-are-not-resettable-here"})
check("an admin cannot be reset through the teacher path", status == 404,
      f"{status} {body}")

print("\n-- signing out --")
teacher = stale

status, body = teacher("DELETE", "/api/staff/session")
check("signing out reports signed out",
      status == 200 and body.get("signedIn") is False, f"{status} {body}")

status, body = teacher("POST", "/api/homework", homework_body)
check("and the staff api is shut again", status == 401, f"{status} {body}")

print(f"\n{'FAILED: ' + ', '.join(failures) if failures else 'All checks passed.'}")
sys.exit(1 if failures else 0)
