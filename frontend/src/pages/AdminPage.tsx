import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";

import {
  createTeacher,
  fetchTeachers,
  setTeacherDisabled,
  signOut,
} from "../api/client";
import type { StaffSession, Teacher } from "../api/types";
import { Field } from "../components/Field";
import { StaffGate } from "../components/StaffGate";

type Status =
  | { kind: "idle" }
  | { kind: "saving" }
  | { kind: "saved"; username: string }
  | { kind: "failed"; message: string };

const BLANK = { username: "", password: "", displayName: "" };

const WHEN = new Intl.DateTimeFormat(undefined, {
  day: "numeric",
  month: "short",
  year: "numeric",
});

export default function AdminPage() {
  return (
    <StaffGate
      needs="admin"
      title="Manage the"
      blurb="staff room."
      children={(who) => <Console who={who} />}
    />
  );
}

function Console({ who }: { who: Extract<StaffSession, { signedIn: true }> }) {
  const [draft, setDraft] = useState(BLANK);
  const [status, setStatus] = useState<Status>({ kind: "idle" });
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setTeachers(await fetchTeachers());
    } catch {
      setTeachers([]);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setStatus({ kind: "saving" });
    try {
      const made = await createTeacher(draft);
      setStatus({ kind: "saved", username: made.username });
      setDraft(BLANK);
      await load();
    } catch (error) {
      setStatus({
        kind: "failed",
        message:
          error instanceof Error ? error.message : "Could not create the account.",
      });
    }
  }

  async function toggle(teacher: Teacher) {
    setBusy(teacher.username);
    try {
      const updated = await setTeacherDisabled(
        teacher.username,
        teacher.disabledAt === null,
      );
      setTeachers((current) =>
        current.map((t) => (t.username === updated.username ? updated : t)),
      );
    } catch (error) {
      setStatus({
        kind: "failed",
        message: error instanceof Error ? error.message : "That did not save.",
      });
    } finally {
      setBusy(null);
    }
  }

  const set = (key: keyof typeof BLANK) => (value: string) =>
    setDraft((current) => ({ ...current, [key]: value }));

  const active = teachers.filter((t) => t.disabledAt === null).length;

  return (
    <>
      <main className="split">
        <section className="copy">
          <p className="crumbs">
            <span className="lead">Administrator</span>
            <span>&middot;</span>
            <span>{who.username}</span>
          </p>

          <h1>
            Manage the
            <br />
            <em>staff room.</em>
          </h1>

          <p className="lede">
            Create an account for each teacher who sets homework. They sign in
            with these details, and whatever they set is{" "}
            <strong>credited to their name</strong>.
          </p>
          <p className="aside">
            Passwords are hashed before they are stored. Nobody can read them back,
            including you.
          </p>

          <ul className="stats">
            <li>
              <span className="label">Teachers</span>
              <span className="value">{teachers.length}</span>
            </li>
            <li>
              <span className="label">Active</span>
              <span className="value good">{active}</span>
            </li>
            <li>
              <span className="label">Disabled</span>
              <span className={teachers.length - active > 0 ? "value bad" : "value"}>
                {teachers.length - active}
              </span>
            </li>
          </ul>
        </section>

        <form className="panel" onSubmit={submit}>
          <div className="panel-head">
            <h2>New teacher</h2>
            <button type="button" className="link" onClick={() => void signOut().then(() => location.reload())}>
              Sign out
            </button>
          </div>
          <div className="form-body">
            <Field label="Full name" value={draft.displayName}
              onChange={set("displayName")} placeholder="Mrs Iyer"
              autoComplete="off" />
            <Field label="Username" data value={draft.username}
              onChange={set("username")} placeholder="mrs.iyer" autoComplete="off" />
            <Field label="Password" value={draft.password} onChange={set("password")}
              type="password" minLength={8} autoComplete="new-password"
              placeholder="At least 8 characters" />
            <div className="submit-row">
              <button type="submit" className="primary" disabled={status.kind === "saving"}>
                {status.kind === "saving" ? "Creating" : "Create account"}
              </button>
              <span className="hint">Give them these details in person</span>
            </div>

            {status.kind === "saved" ? (
              <p className="toast good" role="status">
                Created {status.username}. They can sign in on the teacher page now.
              </p>
            ) : null}
            {status.kind === "failed" ? (
              <p className="toast" role="alert">
                {status.message}
              </p>
            ) : null}
          </div>
        </form>
      </main>

      <div className="board">
        <section className="panel">
          <div className="panel-head">
            <p className="strip">Teacher accounts &middot; {teachers.length}</p>
            <p className="panel-note">
              Disabling ends their session at once. It never deletes their homework.
            </p>
          </div>
          {teachers.length === 0 ? (
            <div className="blank">
              <h3>No teachers yet.</h3>
              <p>Create the first account with the form above.</p>
            </div>
          ) : (
            <ul className="rows actionable">
              {teachers.map((teacher) => {
                const off = teacher.disabledAt !== null;
                return (
                  <li key={teacher.username}>
                    <span className="cell-subject">
                      <i className={off ? "dot crit" : "dot low"} />
                      {off ? "disabled" : "active"}
                    </span>
                    <span className="cell-title">
                      <span className={off ? "name settled" : "name"}>
                        {teacher.displayName}
                      </span>
                      <p className="brief">{teacher.username}</p>
                    </span>
                    <span className="cell-due">
                      Added {WHEN.format(new Date(teacher.createdAt))}
                    </span>
                    <span className={off ? "chip crit" : "chip low"}>
                      {off ? "no access" : "can set work"}
                    </span>
                    <button type="button" className="link"
                      disabled={busy === teacher.username}
                      onClick={() => void toggle(teacher)}>
                      {busy === teacher.username ? "Saving" : off ? "Enable" : "Disable"}
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </section>
      </div>
    </>
  );
}
