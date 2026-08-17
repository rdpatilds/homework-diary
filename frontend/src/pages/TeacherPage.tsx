import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";

import { createHomework, fetchClassHomework, signOut } from "../api/client";
import type { Homework, StaffSession } from "../api/types";
import { Field, TextField } from "../components/Field";
import { StaffGate } from "../components/StaffGate";
import { countdown, dueLabel, localInputToIso, tierOf } from "../deadline";

type Status =
  | { kind: "idle" }
  | { kind: "saving" }
  | { kind: "saved"; title: string }
  | { kind: "failed"; message: string };

type Draft = {
  title: string;
  subject: string;
  details: string;
  className: string;
  section: string;
  dueAt: string;
};

const BLANK: Draft = {
  title: "",
  subject: "",
  details: "",
  className: "",
  section: "",
  dueAt: "",
};

function nowForInput(): string {
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  return now.toISOString().slice(0, 16);
}

export default function TeacherPage() {
  return (
    <StaffGate
      title="Set the work,"
      blurb="set the deadline."
      children={(who) => <Desk who={who} />}
    />
  );
}

function Desk({ who }: { who: Extract<StaffSession, { signedIn: true }> }) {
  const [draft, setDraft] = useState<Draft>(BLANK);
  const [status, setStatus] = useState<Status>({ kind: "idle" });
  const [roster, setRoster] = useState<Homework[]>([]);

  const { className, section } = draft;

  const loadRoster = useCallback(async () => {
    if (!className.trim() || !section.trim()) {
      setRoster([]);
      return;
    }
    try {
      setRoster(await fetchClassHomework(className, section));
    } catch {
      setRoster([]);
    }
  }, [className, section]);

  useEffect(() => {
    void loadRoster();
  }, [loadRoster]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setStatus({ kind: "saving" });
    try {
      const saved = await createHomework({
        ...draft,
        dueAt: localInputToIso(draft.dueAt),
      });
      setStatus({ kind: "saved", title: saved.title });
      setDraft({ ...BLANK, className, section });
      await loadRoster();
    } catch (error) {
      setStatus({
        kind: "failed",
        message: error instanceof Error ? error.message : "Could not set the homework.",
      });
    }
  }

  const set = <K extends keyof Draft>(key: K) => (value: Draft[K]) =>
    setDraft((current) => ({ ...current, [key]: value }));

  const now = new Date();
  const open = roster.filter((h) => new Date(h.dueAt).getTime() > now.getTime());
  const closed = roster.length - open.length;
  const soonest = open[open.length - 1];
  const cohort = className && section ? `${className}-${section}` : null;

  return (
    <>
      <main className="split">
        <section className="copy">
          <p className="crumbs">
            <span className="lead">{who.displayName}</span>
            <span>&middot;</span>
            <span>{cohort ? `Class ${cohort}` : "No class yet"}</span>
            <span>&middot;</span>
            <span>{draft.subject.trim() || "Any subject"}</span>
          </p>

          <h1>
            Set the work,
            <br />
            <em>set the deadline.</em>
          </h1>

          <p className="lede">
            It lands in <strong>every student's diary</strong> for that class the moment
            you save it. They mark it handed in from their own page.
          </p>
          <p className="aside">One form. Not five separate reminders.</p>

          <ul className="stats">
            <li>
              <span className="label">Still open</span>
              <span className="value">{cohort ? open.length : "—"}</span>
            </li>
            <li>
              <span className="label">Next due</span>
              <span className="value warn">
                {soonest ? countdown(soonest.dueAt, now).short : "—"}
              </span>
            </li>
            <li>
              <span className="label">Closed</span>
              <span className="value">{cohort ? closed : "—"}</span>
            </li>
          </ul>
        </section>

        <form className="panel" onSubmit={submit}>
          <div className="panel-head">
            <h2>New homework</h2>
            <button type="button" className="link"
              onClick={() => void signOut().then(() => location.reload())}>
              Sign out
            </button>
          </div>
          <div className="form-body">
            <Field label="Title" value={draft.title} onChange={set("title")}
              placeholder="Photosynthesis lab write-up" />

            <Field label="Subject" value={draft.subject} onChange={set("subject")}
              placeholder="Science" />

            <div className="row-when">
              <Field label="Class" data value={draft.className}
                onChange={set("className")} placeholder="8" />
              <Field label="Section" data value={draft.section}
                onChange={set("section")} placeholder="A" />
              <Field label="Deadline" value={draft.dueAt} onChange={set("dueAt")}
                type="datetime-local" min={nowForInput()} />
            </div>

            <TextField label="What to do" value={draft.details}
              onChange={set("details")} rows={3}
              placeholder="Draw the leaf cross-section and label the chloroplasts." />

            <div className="submit-row">
              <button type="submit" className="primary" disabled={status.kind === "saving"}>
                {status.kind === "saving" ? "Setting" : "Set homework"}
              </button>
              <span className="hint">
                Set by {who.displayName} &middot; delivers to{" "}
                {cohort ? `class ${cohort}` : "no class yet"}
              </span>
            </div>

            {status.kind === "saved" ? (
              <p className="toast good" role="status">
                &ldquo;{status.title}&rdquo; is now in the diary for class {cohort}.
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

      {roster.length > 0 ? (
        <div className="board">
          <section className="panel">
            <div className="panel-head">
              <p className="strip">
                Class {cohort} &middot; {open.length} still open
              </p>
              <p className="panel-note">
                Newest first. Overdue items stay at the top of the student's diary.
              </p>
            </div>
            <ul className="rows">
              {roster.map((item) => {
                const left = countdown(item.dueAt, now);
                const past = new Date(item.dueAt).getTime() <= now.getTime();
                const tier = tierOf(past ? "missed" : "open", left.urgency);
                return (
                  <li key={item.id}>
                    <span className="cell-subject">
                      <i className={`dot ${tier}`} />
                      {item.subject}
                    </span>
                    <span className="cell-title">
                      <span className="name">{item.title}</span>
                    </span>
                    <span className="cell-due">Due {dueLabel(item.dueAt)}</span>
                    <span className={`chip ${tier}`}>
                      {past ? "closed" : `${left.short} left`}
                    </span>
                  </li>
                );
              })}
            </ul>
          </section>
        </div>
      ) : null}
    </>
  );
}
