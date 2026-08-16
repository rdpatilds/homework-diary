"""End-to-end check against a running stack. Proves a teacher can set homework,
that the right student sees it, and that handing it in and taking it back move
it between pending and done. Run it after `docker compose up -d`.

    python verify.py [base-url]     (default http://localhost:8000)

Point it at http://localhost:8080 to check the same paths through nginx.
"""

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
CLASS, SECTION = "VERIFY-7", "Q"
PRIYA = {"className": CLASS, "section": SECTION, "rollNo": "24"}
ARUN = {"className": CLASS, "section": SECTION, "rollNo": "25"}
OUTSIDER = {"className": CLASS, "section": "R", "rollNo": "24"}
failures: list[str] = []


def call(method: str, path: str, body: dict | None = None) -> tuple[int, object]:
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        f"{BASE}{path}", data=data, method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, json.loads(response.read() or b"null")
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read() or b"null")


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{'' if ok else f'  <- {detail}'}")
    if not ok:
        failures.append(name)


def diary(who: dict) -> tuple[int, object]:
    return call("POST", "/api/students/diary", {"studentName": "Verify Student", **who})


def state_of(body: object, homework_id: int) -> str | None:
    if not isinstance(body, dict):
        return None
    for item in body["assignments"]:
        if item["id"] == homework_id:
            return item["status"]["state"]
    return None


print(f"Verifying {BASE}\n")

status, body = call("GET", "/api/health")
check("api is up", status == 200 and body == {"status": "ok"}, f"{status} {body}")

due = (datetime.now(timezone.utc) + timedelta(days=4)).isoformat()
status, created = call("POST", "/api/homework", {
    "title": "Verify run: tectonic plates poster",
    "subject": "Geography", "details": "Trace the ring of fire.",
    "className": CLASS, "section": SECTION,
    "assignedBy": "Verify Script", "dueAt": due,
})
check("teacher can set homework", status == 201, f"{status} {created}")
hw = created["id"] if isinstance(created, dict) and "id" in created else -1

status, body = call("POST", "/api/homework", {
    "title": "Deadline already gone", "subject": "Maths", "details": "",
    "className": CLASS, "section": SECTION, "assignedBy": "Verify Script",
    "dueAt": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
})
check("a deadline in the past is refused", status == 422, f"{status} {body}")

status, body = diary({"className": f"  {CLASS.lower()} ",
                      "section": f" {SECTION.lower()} ", "rollNo": " 24 "})
check("student sees it despite messy casing and spacing",
      status == 200 and state_of(body, hw) == "open", f"{status} {body}")

status, body = diary(OUTSIDER)
check("another section does not see it",
      status == 200 and state_of(body, hw) is None, f"{status} {body}")

status, first = call("POST", f"/api/homework/{hw}/submission", PRIYA)
check("handing it in marks it done",
      status == 200 and isinstance(first, dict)
      and first["status"]["state"] == "done", f"{status} {first}")

status, again = call("POST", f"/api/homework/{hw}/submission", PRIYA)
check("handing it in twice is the same as once",
      status == 200 and isinstance(again, dict)
      and again["status"] == first["status"], f"{status} {again}")

status, body = diary(PRIYA)
check("the diary now shows it done", state_of(body, hw) == "done", f"{status} {body}")

status, body = diary(ARUN)
check("a classmate still owes it", state_of(body, hw) == "open", f"{status} {body}")

status, body = call("POST", f"/api/homework/{hw}/submission", OUTSIDER)
check("another section cannot hand it in", status == 404, f"{status} {body}")

status, body = call("DELETE", f"/api/homework/{hw}/submission", PRIYA)
check("taking it back makes it pending again",
      status == 200 and isinstance(body, dict)
      and body["status"]["state"] == "open", f"{status} {body}")

status, body = call("DELETE", f"/api/homework/{hw}/submission", PRIYA)
check("taking it back twice is the same as once",
      status == 200 and isinstance(body, dict)
      and body["status"]["state"] == "open", f"{status} {body}")

status, body = diary(PRIYA)
check("the diary shows it pending again", state_of(body, hw) == "open", f"{status} {body}")

status, body = diary({"className": CLASS, "section": SECTION, "rollNo": "  "})
check("a blank roll number is refused", status == 422, f"{status} {body}")

status, body = call("GET", f"/api/homework?className={CLASS}&section={SECTION}")
listed = [i["id"] for i in body] if status == 200 else []
check("teacher can list the class", hw in listed, f"{status} {body}")

print(f"\n{'FAILED: ' + ', '.join(failures) if failures else 'All checks passed.'}")
sys.exit(1 if failures else 0)
