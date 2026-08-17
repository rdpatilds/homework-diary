import { useCallback, useEffect, useState } from "react";
import type { FormEvent, ReactNode } from "react";

import { fetchSession, signIn } from "../api/client";
import type { Role, StaffSession } from "../api/types";
import { Field } from "./Field";

type Gate =
  | { kind: "checking" }
  | { kind: "locked"; error: string | null; busy: boolean }
  | { kind: "open"; who: Extract<StaffSession, { signedIn: true }> };

/** Wraps a staff page. Nothing inside renders until the server says who you
 * are, and the server checks again on every call the page makes. This gate is
 * for the person, not for the data. */
export function StaffGate({
  needs,
  title,
  blurb,
  children,
}: {
  needs?: Role;
  title: string;
  blurb: string;
  children: (
    who: Extract<StaffSession, { signedIn: true }>,
    refresh: () => void,
  ) => ReactNode;
}) {
  const [gate, setGate] = useState<Gate>({ kind: "checking" });
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const look = useCallback(async () => {
    try {
      const session = await fetchSession();
      setGate(
        session.signedIn
          ? { kind: "open", who: session }
          : { kind: "locked", error: null, busy: false },
      );
    } catch {
      setGate({
        kind: "locked",
        error: "Cannot reach the server. Check that the API is running.",
        busy: false,
      });
    }
  }, []);

  useEffect(() => {
    void look();
  }, [look]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setGate({ kind: "locked", error: null, busy: true });
    try {
      const session = await signIn(username, password);
      setPassword("");
      setGate(
        session.signedIn
          ? { kind: "open", who: session }
          : { kind: "locked", error: "Sign in failed.", busy: false },
      );
    } catch (error) {
      setPassword("");
      setGate({
        kind: "locked",
        error: error instanceof Error ? error.message : "Sign in failed.",
        busy: false,
      });
    }
  }

  if (gate.kind === "checking") {
    return (
      <main className="split">
        <section className="copy">
          <p className="crumbs">
            <span className="lead">Staff</span>
            <span>&middot;</span>
            <span>Checking your session</span>
          </p>
        </section>
      </main>
    );
  }

  if (gate.kind === "open") {
    if (needs && gate.who.role !== needs) {
      return (
        <main className="split">
          <section className="copy">
            <p className="crumbs">
              <span className="lead">Staff</span>
              <span>&middot;</span>
              <span>{gate.who.role}</span>
            </p>
            <h1>
              Not your page,
              <br />
              <em>{gate.who.displayName}.</em>
            </h1>
            <p className="lede">
              Only an <strong>administrator</strong> can manage teacher accounts.
              You are signed in as a {gate.who.role}.
            </p>
          </section>
        </main>
      );
    }
    return <>{children(gate.who, look)}</>;
  }

  return (
    <main className="split">
      <section className="copy">
        <p className="crumbs">
          <span className="lead">Staff</span>
          <span>&middot;</span>
          <span>Sign in required</span>
        </p>
        <h1>
          {title}
          <br />
          <em>{blurb}</em>
        </h1>
        <p className="lede">
          Staff accounts are created by an administrator. Students never sign in.
        </p>
      </section>

      <form className="panel" onSubmit={submit}>
        <div className="panel-head">
          <h2>Sign in</h2>
          <span className="tag">Staff</span>
        </div>
        <div className="form-body">
          <Field label="Username" data value={username} onChange={setUsername}
            autoComplete="username" placeholder="mrs.iyer" />
          <Field label="Password" value={password} onChange={setPassword}
            type="password" autoComplete="current-password" />
          <div className="submit-row">
            <button type="submit" className="primary" disabled={gate.busy}>
              {gate.busy ? "Signing in" : "Sign in"}
            </button>
            <span className="hint">Session lasts 12 hours</span>
          </div>
          {gate.error ? (
            <p className="toast" role="alert">
              {gate.error}
            </p>
          ) : null}
        </div>
      </form>
    </main>
  );
}
