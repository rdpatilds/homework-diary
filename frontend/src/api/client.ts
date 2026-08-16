import type { Homework, NewHomework, PendingHomework, Student } from "./types";

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

export function fetchPendingHomework(student: Student): Promise<PendingHomework> {
  return request("/api/students/homework", {
    method: "POST",
    body: JSON.stringify(student),
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
