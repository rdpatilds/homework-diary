import { useState } from "react";
import type { FormEvent } from "react";

import { fetchPendingHomework } from "../api/client";
import type { PendingHomework, Student } from "../api/types";
import { Field } from "../components/Field";
import { countdown, dueLabel } from "../deadline";

type Screen =
  | { kind: "identify"; error: string | null }
  | { kind: "loading" }
  | { kind: "diary"; data: PendingHomework };

const BLANK: Student = { studentName: "", rollNo: "", className: "", section: "" };

export default function StudentPage() {
  const [details, setDetails] = useState<Student>(BLANK);
  const [screen, setScreen] = useState<Screen>({ kind: "identify", error: null });

  async function submit(event: FormEvent) {
    event.preventDefault();
    setScreen({ kind: "loading" });
    try {
      setScreen({ kind: "diary", data: await fetchPendingHomework(details) });
    } catch (error) {
      setScreen({
        kind: "identify",
        error: error instanceof Error ? error.message : "Something went wrong.",
      });
    }
  }

  if (screen.kind === "diary") {
    return (
      <Diary
        data={screen.data}
        onChangeStudent={() => setScreen({ kind: "identify", error: null })}
      />
    );
  }

  const busy = screen.kind === "loading";
  return (
    <main className="sheet">
      <div className="masthead">
        <p className="eyebrow">Meridian School &middot; Homework Diary</p>
        <h1>What's due?</h1>
        <p className="identity">Fill in the cover and we'll open your diary.</p>
      </div>
      <form className="cover" onSubmit={submit}>
        <Field
          label="Name"
          value={details.studentName}
          onChange={(studentName) => setDetails({ ...details, studentName })}
          autoComplete="name"
        />
        <Field
          label="Roll no."
          value={details.rollNo}
          onChange={(rollNo) => setDetails({ ...details, rollNo })}
          inputMode="numeric"
        />
        <Field
          label="Class"
          value={details.className}
          onChange={(className) => setDetails({ ...details, className })}
          placeholder="8"
        />
        <Field
          label="Section"
          value={details.section}
          onChange={(section) => setDetails({ ...details, section })}
          placeholder="A"
        />
        <div className="actions">
          <button type="submit" disabled={busy}>
            {busy ? "Opening" : "Open my diary"}
          </button>
        </div>
      </form>
      {screen.kind === "identify" && screen.error ? (
        <p className="notice" role="alert">
          {screen.error}
        </p>
      ) : null}
    </main>
  );
}

function Diary({
  data,
  onChangeStudent,
}: {
  data: PendingHomework;
  onChangeStudent: () => void;
}) {
  const asOf = new Date(data.asOf);
  const { student, items } = data;
  return (
    <main className="sheet">
      <div className="masthead">
        <p className="eyebrow">Meridian School &middot; Homework Diary</p>
        <h1>
          {items.length === 0 ? "You're all clear," : "Still to do,"}
          <br />
          {student.studentName}.
        </h1>
        <p className="identity">
          <span>
            Class {student.className}-{student.section}
          </span>
          <span>Roll {student.rollNo}</span>
          <span>
            {items.length} {items.length === 1 ? "assignment" : "assignments"} open
          </span>
          <button type="button" className="link" onClick={onChangeStudent}>
            Not you?
          </button>
        </p>
      </div>
      {items.length === 0 ? (
        <div className="empty">
          <h2>Nothing is due.</h2>
          <p>
            No open homework for class {student.className}-{student.section}. Check
            back after your next lesson.
          </p>
        </div>
      ) : (
        <div className="ledger">
          {items.map((item, index) => {
            const left = countdown(item.dueAt, asOf);
            return (
              <article
                key={item.id}
                className="entry"
                style={{ animationDelay: `${index * 60}ms` }}
              >
                <p className={`count ${left.urgency}`}>
                  <span className="count-value">{left.value}</span>
                  <span className="count-unit">{left.unit} left</span>
                </p>
                <div className="entry-body">
                  <h2 className="entry-title">{item.title}</h2>
                  <p className="entry-meta">
                    {item.subject} &middot; due {dueLabel(item.dueAt)} &middot;{" "}
                    {item.assignedBy}
                  </p>
                  {item.details ? <p className="entry-details">{item.details}</p> : null}
                </div>
              </article>
            );
          })}
        </div>
      )}
    </main>
  );
}
