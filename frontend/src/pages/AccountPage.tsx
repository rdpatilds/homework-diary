import { useState } from "react";
import type { FormEvent } from "react";

import { changePassword, signOut } from "../api/client";
import type { StaffSession } from "../api/types";
import { Field } from "../components/Field";
import { StaffGate } from "../components/StaffGate";

type Status =
  | { kind: "idle" }
  | { kind: "saving" }
  | { kind: "saved" }
  | { kind: "failed"; message: string };

const BLANK = { current: "", next: "", again: "" };

export default function AccountPage() {
  return (
    <StaffGate
      title="Your account,"
      blurb="your password."
      children={(who) => <Account who={who} />}
    />
  );
}

function Account({ who }: { who: Extract<StaffSession, { signedIn: true }> }) {
  const [form, setForm] = useState(BLANK);
  const [status, setStatus] = useState<Status>({ kind: "idle" });

  const mismatch = form.again.length > 0 && form.next !== form.again;
  const tooShort = form.next.length > 0 && form.next.length < 8;
  const ready =
    form.current.length > 0 && form.next.length >= 8 && form.next === form.again;

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!ready) return;
    setStatus({ kind: "saving" });
    try {
      await changePassword(form.current, form.next);
      setForm(BLANK);
      setStatus({ kind: "saved" });
    } catch (error) {
      setStatus({
        kind: "failed",
        message:
          error instanceof Error ? error.message : "Could not change the password.",
      });
    }
  }

  const set = (key: keyof typeof BLANK) => (value: string) =>
    setForm((current) => ({ ...current, [key]: value }));

  return (
    <main className="split">
      <section className="copy">
        <p className="crumbs">
          <span className="lead">{who.role === "admin" ? "Administrator" : "Teacher"}</span>
          <span>&middot;</span>
          <span>{who.username}</span>
        </p>

        <h1>
          Your account,
          <br />
          <em>{who.displayName}.</em>
        </h1>

        <p className="lede">
          Pick something <strong>at least 8 characters</strong> that you do not use
          anywhere else. You will need your current password to change it.
        </p>
        <p className="aside">
          Changing it signs you out everywhere else. Any other browser or phone still
          holding your account will have to sign in again.
        </p>

        <ul className="legend">
          <li>
            <span className="head">
              <i className="dot low" />
              Stored hashed
            </span>
            <p>Nobody can read your password back, including an administrator.</p>
          </li>
          <li>
            <span className="head">
              <i className="dot med" />
              Forgotten it?
            </span>
            <p>
              {who.role === "admin"
                ? "Reset it from the environment file and restart the API."
                : "An administrator can issue you a new one."}
            </p>
          </li>
          <li>
            <span className="head">
              <i className="dot crit" />
              Never share it
            </span>
            <p>Homework you set is credited to your name.</p>
          </li>
        </ul>
      </section>

      <form className="panel" onSubmit={submit}>
        <div className="panel-head">
          <h2>Change password</h2>
          <button type="button" className="link"
            onClick={() => void signOut().then(() => location.reload())}>
            Sign out
          </button>
        </div>
        <div className="form-body">
          <Field label="Current password" value={form.current} onChange={set("current")}
            type="password" autoComplete="current-password" />
          <Field label="New password" value={form.next} onChange={set("next")}
            type="password" autoComplete="new-password" minLength={8}
            placeholder="At least 8 characters" />
          <Field label="New password again" value={form.again} onChange={set("again")}
            type="password" autoComplete="new-password" />

          <div className="submit-row">
            <button type="submit" className="primary"
              disabled={!ready || status.kind === "saving"}>
              {status.kind === "saving" ? "Changing" : "Change password"}
            </button>
            <span className="hint">
              {tooShort
                ? "Too short"
                : mismatch
                  ? "The two do not match"
                  : "Signs you out everywhere else"}
            </span>
          </div>

          {status.kind === "saved" ? (
            <p className="toast good" role="status">
              Password changed. Every other session has been signed out.
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
  );
}
