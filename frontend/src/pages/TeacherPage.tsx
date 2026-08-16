import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";

import { createHomework, fetchClassHomework } from "../api/client";
import type { Homework } from "../api/types";
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

  return (
    <main className="sheet teacher">
      <div className="masthead">
        <p className="eyebrow">Meridian School &middot; Staff</p>
        <h1>Set homework.</h1>
        <p className="identity">
          <span>It appears in every student's diary in that class straight away.</span>
        </p>
      </div>

      <form className="cover wide" onSubmit={submit}>
        <Field label="Title" value={draft.title} onChange={set("title")} span={6}
          placeholder="Photosynthesis lab write-up" />
        <Field label="Subject" value={draft.subject} onChange={set("subject")} span={3}
          placeholder="Science" />
        <Field label="Set by" value={draft.assignedBy} onChange={set("assignedBy")}
          span={3} placeholder="Mrs Iyer" autoComplete="name" />
        <Field label="Class" value={draft.className} onChange={set("className")}
          span={1} placeholder="8" />
        <Field label="Section" value={draft.section} onChange={set("section")}
          span={1} placeholder="A" />
        <Field label="Deadline" value={draft.dueAt} onChange={set("dueAt")}
          type="datetime-local" min={nowForInput()} span={4} />
        <TextField label="What to do" value={draft.details} onChange={set("details")}
          span={6} rows={3}
          placeholder="Draw the leaf cross-section and label the chloroplasts." />
        <div className="actions">
          <button type="submit" disabled={status.kind === "saving"}>
            {status.kind === "saving" ? "Setting" : "Set homework"}
          </button>
        </div>
      </form>

      {status.kind === "saved" ? (
        <p className="notice good" role="status">
          Set. &ldquo;{status.title}&rdquo; is now in the diary for class {className}-
          {section}.
        </p>
      ) : null}
      {status.kind === "failed" ? (
        <p className="notice" role="alert">
          {status.message}
        </p>
      ) : null}

      {roster.length > 0 ? (
        <>
          <ul className="roster">
            {roster.map((item) => {
              const past = new Date(item.dueAt).getTime() <= Date.now();
              return (
                <li key={item.id} className={past ? "past" : undefined}>
                  <strong>{item.title}</strong>
                  <span>{item.subject}</span>
                  <span className="when">
                    {past ? "closed" : "due"} {dueLabel(item.dueAt)}
                  </span>
                </li>
              );
            })}
          </ul>
          <p className="eyebrow" style={{ marginTop: "0.75rem" }}>
            Everything set for class {className}-{section}
          </p>
        </>
      ) : null}
    </main>
  );
}
