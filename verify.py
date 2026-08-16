"""End-to-end check against a running stack. Proves a teacher can set homework
and the right student sees it. Run it after `docker compose up -d`.

    python verify.py [base-url]     (default http://localhost:8000)
"""

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
CLASS, SECTION = "VERIFY-7", "Q"
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
homework_id = created.get("id") if isinstance(created, dict) else None

status, body = call("POST", "/api/homework", {
    "title": "Deadline already gone", "subject": "Maths", "details": "",
    "className": CLASS, "section": SECTION, "assignedBy": "Verify Script",
    "dueAt": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
})
check("a deadline in the past is refused", status == 422, f"{status} {body}")

status, body = call("POST", "/api/students/homework", {
    "studentName": "Verify Student", "rollNo": "01",
    "className": f"  {CLASS.lower()} ", "section": f" {SECTION.lower()} ",
})
found = [i["id"] for i in body["items"]] if status == 200 else []
check("student sees it despite messy casing and spacing",
      status == 200 and homework_id in found, f"{status} {body}")

status, body = call("POST", "/api/students/homework", {
    "studentName": "Other Section", "rollNo": "02",
    "className": CLASS, "section": "R",
})
other = [i["id"] for i in body["items"]] if status == 200 else []
check("another section does not see it", status == 200 and homework_id not in other,
      f"{status} {body}")

status, body = call("POST", "/api/students/homework", {
    "studentName": "  ", "rollNo": "03", "className": CLASS, "section": SECTION,
})
check("a blank name is refused", status == 422, f"{status} {body}")

status, body = call("GET", f"/api/homework?className={CLASS}&section={SECTION}")
listed = [i["id"] for i in body] if status == 200 else []
check("teacher can list the class", homework_id in listed, f"{status} {body}")

print(f"\n{'FAILED: ' + ', '.join(failures) if failures else 'All checks passed.'}")
sys.exit(1 if failures else 0)
