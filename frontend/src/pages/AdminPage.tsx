import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";

import {
  createStaff,
  fetchStaff,
  resetStaffPassword,
  setStaffDisabled,
  signOut,
} from "../api/client";
import type { Role, StaffMember, StaffSession } from "../api/types";
import { Field } from "../components/Field";
import { StaffGate } from "../components/StaffGate";

type Status =
  | { kind: "idle" }
  | { kind: "saving" }
  | { kind: "saved"; username: string; role: Role }
  | { kind: "failed"; message: string };

const BLANK = { username: "", password: "", displayName: "", role: "teacher" as Role };

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
  const [staff, setStaff] = useState<StaffMember[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [resetting, setResetting] = useState<{ username: string; password: string } | null>(
    null,
  );
  const [reset, setReset] = useState<{ username: string } | null>(null);

  const load = useCallback(async () => {
    try {
      setStaff(await fetchStaff());
    } catch {
      setStaff([]);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setStatus({ kind: "saving" });
    try {
      const made = await createStaff(draft);
      setStatus({ kind: "saved", username: made.username, role: made.role });
      setDraft({ ...BLANK, role: draft.role });
      await load();
    } catch (error) {
      setStatus({
        kind: "failed",
        message:
          error instanceof Error ? error.message : "Could not create the account.",
      });
    }
  }

  async function toggle(member: StaffMember) {
    setBusy(member.username);
    setStatus({ kind: "idle" });
    try {
      const updated = await setStaffDisabled(
        member.username,
        member.disabledAt === null,
      );
      setStaff((current) =>
        current.map((s) => (s.username === updated.username ? updated : s)),
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

  async function submitReset(event: FormEvent) {
    event.preventDefault();
    if (!resetting || resetting.password.length < 8) return;
    setBusy(resetting.username);
    try {
      await resetStaffPassword(resetting.username, resetting.password);
      setReset({ username: resetting.username });
      setResetting(null);
    } catch (error) {
      setStatus({
        kind: "failed",
        message: error instanceof Error ? error.message : "Could not reset it.",
      });
    } finally {
      setBusy(null);
    }
  }

  const set = (key: "username" | "password" | "displayName") => (value: string) =>
    setDraft((current) => ({ ...current, [key]: value }));

  const admins = staff.filter((s) => s.role === "admin");
  const activeAdmins = admins.filter((s) => s.disabledAt === null).length;
  const teachers = staff.filter((s) => s.role === "teacher");
  const disabled = staff.filter((s) => s.disabledAt !== null).length;

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
            Create an account for each teacher who sets homework, and for anyone who
            needs to <strong>manage accounts themselves</strong>. Whatever a teacher
            sets is credited to their name.
          </p>
          <p className="aside">
            Passwords are hashed before they are stored. Nobody can read them back,
            including you.
          </p>

          <ul className="stats">
            <li>
              <span className="label">Admins</span>
              <span className="value">{admins.length}</span>
            </li>
            <li>
              <span className="label">Teachers</span>
              <span className="value good">{teachers.length}</span>
            </li>
            <li>
              <span className="label">Disabled</span>
              <span className={disabled > 0 ? "value bad" : "value"}>{disabled}</span>
            </li>
          </ul>
        </section>

        <form className="panel" onSubmit={submit}>
          <div className="panel-head">
            <h2>New account</h2>
            <span className="row-actions">
              <Link className="link" to="/account">
                My password
              </Link>
              <button type="button" className="link"
                onClick={() => void signOut().then(() => location.reload())}>
                Sign out
              </button>
            </span>
          </div>
          <div className="form-body">
            <fieldset className="segments">
              <legend>Role</legend>
              {(["teacher", "admin"] as const).map((role) => (
                <label key={role}>
                  <input type="radio" name="role" value={role}
                    checked={draft.role === role}
                    onChange={() => setDraft((c) => ({ ...c, role }))} />
                  <span>{role === "teacher" ? "Teacher" : "Administrator"}</span>
                </label>
              ))}
            </fieldset>
            <p className="segments-note">
              {draft.role === "admin"
                ? "Can create and disable accounts, and set homework."
                : "Can set homework for any class."}
            </p>

            <Field label="Full name" value={draft.displayName}
              onChange={set("displayName")} placeholder="Mrs Iyer" autoComplete="off" />
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
                Created {status.username} as {status.role === "admin" ? "an administrator" : "a teacher"}.
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
            <p className="strip">Staff accounts &middot; {staff.length}</p>
            <p className="panel-note">
              {activeAdmins === 1
                ? "Only one active administrator. Add another before disabling anyone."
                : "Disabling ends their session at once. It never deletes their homework."}
            </p>
          </div>
          {staff.length === 0 ? (
            <div className="blank">
              <h3>No accounts yet.</h3>
              <p>Create the first one with the form above.</p>
            </div>
          ) : (
            <ul className="rows actionable">
              {staff.map((member) => {
                const off = member.disabledAt !== null;
                const isAdmin = member.role === "admin";
                const isYou = member.username === who.username;
                const lastAdmin = isAdmin && !off && activeAdmins === 1;
                return (
                  <li key={member.username}>
                    <span className="cell-subject">
                      <i className={off ? "dot crit" : isAdmin ? "dot med" : "dot low"} />
                      {isAdmin ? "admin" : "teacher"}
                    </span>
                    <span className="cell-title">
                      <span className={off ? "name settled" : "name"}>
                        {member.displayName}
                        {isYou ? <em className="you"> you</em> : null}
                      </span>
                      <p className="brief">{member.username}</p>
                    </span>
                    <span className="cell-due">
                      Added {WHEN.format(new Date(member.createdAt))}
                    </span>
                    <span className={off ? "chip crit" : isAdmin ? "chip med" : "chip low"}>
                      {off ? "no access" : isAdmin ? "manages accounts" : "can set work"}
                    </span>
                    <span className="row-actions">
                      {isYou ? null : (
                        <button type="button" className="link"
                          disabled={busy === member.username}
                          onClick={() =>
                            setResetting(
                              resetting?.username === member.username
                                ? null
                                : { username: member.username, password: "" },
                            )
                          }>
                          {resetting?.username === member.username ? "Cancel" : "Reset"}
                        </button>
                      )}
                      <button type="button" className="link"
                        disabled={busy === member.username || isYou || lastAdmin}
                        title={
                          isYou
                            ? "You cannot disable your own account"
                            : lastAdmin
                              ? "The only active administrator"
                              : undefined
                        }
                        onClick={() => void toggle(member)}>
                        {busy === member.username ? "Saving" : off ? "Enable" : "Disable"}
                      </button>
                    </span>

                    {resetting?.username === member.username ? (
                      <form className="row-inline" onSubmit={submitReset}>
                        <input type="password" autoFocus minLength={8}
                          placeholder={`New password for ${member.username}`}
                          value={resetting.password}
                          onChange={(event) =>
                            setResetting({
                              username: member.username,
                              password: event.target.value,
                            })
                          } />
                        <button type="submit" className="primary"
                          disabled={resetting.password.length < 8}>
                          Set it
                        </button>
                        <span className="hint">
                          Ends their session. Tell them in person.
                        </span>
                      </form>
                    ) : null}

                    {reset?.username === member.username ? (
                      <p className="row-inline note" role="status">
                        New password set for {member.username}. They have been signed
                        out.
                      </p>
                    ) : null}
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
