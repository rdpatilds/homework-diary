import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";

import { createHomework, fetchClassHomework } from "../api/client";
import type { Homework } from "../api/types";
import { CurveField } from "../components/CurveField";
import { Field, TextField } from "../components/Field";
import { dueLabel, localInputToIso } from "../deadline";

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
  assignedBy: string;
  dueAt: string;
};

const BLANK: Draft = {
  title: "",
  subject: "",
  details: "",
  className: "",
  section: "",
  assignedBy: "",
  dueAt: "",
};

function nowForInput(): string {
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  return now.toISOString().slice(0, 16);
}

export default function TeacherPage() {
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
      setDraft({ ...BLANK, className, section, assignedBy: draft.assignedBy });
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

  const open = roster.filter((h) => new Date(h.dueAt).getTime() > Date.now()).length;

  return (
    <>
      <section className="hero">
        <CurveField tone="cyan" />
        <div className="hero-inner">
          <div>
            <p className="badge">
              Staff <b>{className && section ? `${className}-${section}` : "any class"}</b>
            </p>
            <h1>
              Set the work,
              <br />
              <em>set the deadline.</em>
            </h1>
            <p className="lede">
              It lands in <b>every student's diary</b> for that class the moment you
              save it. They mark it handed in from their own page.
            </p>
          </div>

          <form className="panel cover wide" onSubmit={submit}>
            <div className="panel-head c6">
              <h2>New homework</h2>
              <p className="eyebrow">Teacher</p>
            </div>
            <Field label="Title" span={6} value={draft.title} onChange={set("title")}
              placeholder="Photosynthesis lab write-up" />
            <Field label="Subject" span={3} value={draft.subject} onChange={set("subject")}
              placeholder="Science" />
            <Field label="Set by" span={3} value={draft.assignedBy}
              onChange={set("assignedBy")} placeholder="Mrs Iyer" autoComplete="name" />
            <Field label="Class" span={1} value={draft.className}
              onChange={set("className")} placeholder="8" />
            <Field label="Section" span={1} value={draft.section}
              onChange={set("section")} placeholder="A" />
            <Field label="Deadline" span={4} value={draft.dueAt} onChange={set("dueAt")}
              type="datetime-local" min={nowForInput()} />
            <TextField label="What to do" span={6} value={draft.details}
              onChange={set("details")} rows={3}
              placeholder="Draw the leaf cross-section and label the chloroplasts." />
            <div className="actions">
              <button type="submit" disabled={status.kind === "saving"}>
                {status.kind === "saving" ? "Setting" : "Set homework"}
              </button>
            </div>
            {status.kind === "saved" ? (
              <p className="notice good c6" role="status">
                Set. &ldquo;{status.title}&rdquo; is now in the diary for class{" "}
                {className}-{section}.
              </p>
            ) : null}
            {status.kind === "failed" ? (
              <p className="notice c6" role="alert">
                {status.message}
              </p>
            ) : null}
          </form>
        </div>
      </section>

      {roster.length > 0 ? (
        <div className="board">
          <section className="section">
            <div className="section-head">
              <h2>
                Class {className}-{section} &middot; {open} still open
              </h2>
              <span className="rule" />
            </div>
            <ul className="roster">
              {roster.map((item) => {
                const past = new Date(item.dueAt).getTime() <= Date.now();
                return (
                  <li key={item.id} className={past ? "past" : undefined}>
                    <span className="subject">
                      <i className={past ? "dot missed" : "dot open"} />
                      {item.subject}
                    </span>
                    <strong>{item.title}</strong>
                    <span className="when">
                      {past ? "closed" : "due"} {dueLabel(item.dueAt)}
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
