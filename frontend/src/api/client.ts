import type {
  Assignment,
  Homework,
  NewHomework,
  NewStaff,
  StaffMember,
  StaffSession,
  Student,
  StudentDiary,
  StudentRef,
} from "./types";

/** FastAPI answers with `detail` as either a plain string or a list of
 * per-field errors. Flatten both here so no caller has to know. */
function readDetail(body: unknown): string | null {
  if (typeof body !== "object" || body === null) return null;
  const detail = (body as { detail?: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (!Array.isArray(detail)) return null;
  const messages = detail.flatMap((entry) => {
    if (typeof entry !== "object" || entry === null) return [];
    const { loc, msg } = entry as { loc?: unknown; msg?: unknown };
    if (typeof msg !== "string") return [];
    const field = Array.isArray(loc) ? loc[loc.length - 1] : undefined;
    return [typeof field === "string" && field !== "body" ? `${field}: ${msg}` : msg];
  });
  return messages.length ? messages.join(". ") : null;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      ...init,
      // The staff session is an HttpOnly cookie, so nothing here handles a
      // token. It just has to travel.
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new Error("Cannot reach the server. Check that the API is running.");
  }
  const body = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(readDetail(body) ?? `Request failed (${response.status})`);
  }
  return body as T;
}

export function fetchDiary(student: Student): Promise<StudentDiary> {
  return request("/api/students/diary", {
    method: "POST",
    body: JSON.stringify(student),
  });
}

export function handIn(homeworkId: number, who: StudentRef): Promise<Assignment> {
  return request(`/api/homework/${homeworkId}/submission`, {
    method: "POST",
    body: JSON.stringify(who),
  });
}

export function takeBack(homeworkId: number, who: StudentRef): Promise<Assignment> {
  return request(`/api/homework/${homeworkId}/submission`, {
    method: "DELETE",
    body: JSON.stringify(who),
  });
}

export function createHomework(homework: NewHomework): Promise<Homework> {
  return request("/api/homework", {
    method: "POST",
    body: JSON.stringify(homework),
  });
}

export function fetchClassHomework(
  className: string,
  section: string,
): Promise<Homework[]> {
  const query = new URLSearchParams({ className, section });
  return request(`/api/homework?${query}`);
}

export function fetchSession(): Promise<StaffSession> {
  return request("/api/staff/session");
}

export function signIn(username: string, password: string): Promise<StaffSession> {
  return request("/api/staff/session", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function signOut(): Promise<StaffSession> {
  return request("/api/staff/session", { method: "DELETE" });
}

export function fetchStaff(): Promise<StaffMember[]> {
  return request("/api/admin/staff");
}

export function createStaff(member: NewStaff): Promise<StaffMember> {
  return request("/api/admin/staff", {
    method: "POST",
    body: JSON.stringify(member),
  });
}

export function changePassword(
  currentPassword: string,
  newPassword: string,
): Promise<StaffSession> {
  return request("/api/staff/password", {
    method: "POST",
    body: JSON.stringify({ currentPassword, newPassword }),
  });
}

export function resetStaffPassword(
  username: string,
  password: string,
): Promise<StaffMember> {
  return request(`/api/admin/staff/${encodeURIComponent(username)}/password`, {
    method: "POST",
    body: JSON.stringify({ password }),
  });
}

export function setStaffDisabled(
  username: string,
  disabled: boolean,
): Promise<StaffMember> {
  return request(
    `/api/admin/staff/${encodeURIComponent(username)}/disabled?disabled=${disabled}`,
    { method: "POST" },
  );
}
