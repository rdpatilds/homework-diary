import { useState } from "react";
import type { FormEvent } from "react";

import { fetchDiary, handIn, takeBack } from "../api/client";
import type { Assignment, Student, StudentDiary } from "../api/types";
import { Field } from "../components/Field";
import { countdown, dueLabel } from "../deadline";

type Screen =
  | { kind: "identify"; error: string | null }
  | { kind: "loading" }
  | { kind: "diary"; data: StudentDiary; busy: number | null; error: string | null };

const BLANK: Student = { studentName: "", rollNo: "", className: "", section: "" };

export default function StudentPage() {
  const [details, setDetails] = useState<Student>(BLANK);
  const [screen, setScreen] = useState<Screen>({ kind: "identify", error: null });

  async function open(event: FormEvent) {
    event.preventDefault();
    setScreen({ kind: "loading" });
    try {
      const data = await fetchDiary(details);
      setScreen({ kind: "diary", data, busy: null, error: null });
    } catch (error) {
      setScreen({
        kind: "identify",
        error: error instanceof Error ? error.message : "Something went wrong.",
      });
    }
  }

  async function toggle(item: Assignment) {
    if (screen.kind !== "diary") return;
    const { student } = screen.data;
    const who = {
      className: student.className,
      section: student.section,
      rollNo: student.rollNo,
    };
    setScreen({ ...screen, busy: item.id, error: null });
    try {
      const updated =
        item.status.state === "done"
          ? await takeBack(item.id, who)
          : await handIn(item.id, who);
      setScreen((current) =>
        current.kind === "diary"
          ? {
              ...current,
              busy: null,
              data: {
                ...current.data,
                assignments: current.data.assignments.map((a) =>
                  a.id === updated.id ? updated : a,
                ),
              },
            }
          : current,
      );
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "That did not save. Try again.";
      setScreen((current) =>
        current.kind === "diary" ? { ...current, busy: null, error: message } : current,
      );
    }
  }

  if (screen.kind === "diary") {
    return (
      <Diary
        screen={screen}
        onToggle={toggle}
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
      <form className="cover" onSubmit={open}>
        <Field label="Name" value={details.studentName}
          onChange={(studentName) => setDetails({ ...details, studentName })}
          autoComplete="name" />
        <Field label="Roll no." value={details.rollNo}
          onChange={(rollNo) => setDetails({ ...details, rollNo })} inputMode="numeric" />
        <Field label="Class" value={details.className}
          onChange={(className) => setDetails({ ...details, className })} placeholder="8" />
        <Field label="Section" value={details.section}
          onChange={(section) => setDetails({ ...details, section })} placeholder="A" />
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
  screen,
  onToggle,
  onChangeStudent,
}: {
  screen: Extract<Screen, { kind: "diary" }>;
  onToggle: (item: Assignment) => void;
  onChangeStudent: () => void;
}) {
  const { student, asOf, assignments } = screen.data;
  const at = new Date(asOf);
  const missed = assignments.filter((a) => a.status.state === "missed");
  const todo = assignments.filter((a) => a.status.state === "open");
  const done = assignments.filter((a) => a.status.state === "done");

  const ledger = (items: Assignment[]) => (
    <div className="ledger">
      {items.map((item, index) => (
        <Entry
          key={item.id}
          item={item}
          asOf={at}
          index={index}
          busy={screen.busy === item.id}
          onToggle={onToggle}
        />
      ))}
    </div>
  );

  return (
    <main className="sheet">
      <div className="masthead">
        <p className="eyebrow">Meridian School &middot; Homework Diary</p>
        <h1>
          {todo.length + missed.length === 0 ? "You're all clear," : "Still to do,"}
          <br />
          {student.studentName}.
        </h1>
        <p className="identity">
          <span>
            Class {student.className}-{student.section}
          </span>
          <span>Roll {student.rollNo}</span>
          <span>{todo.length} to do</span>
          {missed.length > 0 ? <span className="tally-late">{missed.length} missed</span> : null}
          {done.length > 0 ? <span>{done.length} handed in</span> : null}
          <button type="button" className="link" onClick={onChangeStudent}>
            Not you?
          </button>
        </p>
      </div>

      {screen.error ? (
        <p className="notice" role="alert">
          {screen.error}
        </p>
      ) : null}

      {missed.length > 0 ? (
        <section>
          <p className="ledger-heading late">Past the deadline</p>
          {ledger(missed)}
        </section>
      ) : null}

      {todo.length > 0 ? (
        <section>
          {missed.length > 0 ? <p className="ledger-heading">Still to do</p> : null}
          {ledger(todo)}
        </section>
      ) : null}

      {todo.length === 0 && missed.length === 0 ? (
        <div className="empty">
          <h2>Nothing is due.</h2>
          <p>
            No open homework for class {student.className}-{student.section}. Check
            back after your next lesson.
          </p>
        </div>
      ) : null}

      {done.length > 0 ? (
        <section>
          <p className="ledger-heading done">Handed in</p>
          {ledger(done)}
        </section>
      ) : null}
    </main>
  );
}

function Entry({
  item,
  asOf,
  index,
  busy,
  onToggle,
}: {
  item: Assignment;
  asOf: Date;
  index: number;
  busy: boolean;
  onToggle: (item: Assignment) => void;
}) {
  const left = countdown(item.dueAt, asOf);
  const isDone = item.status.state === "done";
  return (
    <article className="entry" style={{ animationDelay: `${index * 60}ms` }}>
      {isDone ? (
        <p className="count done">
          <span className="count-value" aria-hidden="true">
            &#10003;
          </span>
          <span className="count-unit">handed in</span>
        </p>
      ) : (
        <p className={`count ${left.urgency}`}>
          <span className="count-value">{left.value}</span>
          <span className="count-unit">
            {left.unit} {item.status.state === "missed" ? "late" : "left"}
          </span>
        </p>
      )}
      <div className={isDone ? "entry-body settled" : "entry-body"}>
        <h2 className="entry-title">{item.title}</h2>
        <p className="entry-meta">
          {item.subject} &middot; due {dueLabel(item.dueAt)} &middot; {item.assignedBy}
        </p>
        {item.details && !isDone ? <p className="entry-details">{item.details}</p> : null}
        <button
          type="button"
          className="link"
          disabled={busy}
          onClick={() => onToggle(item)}
        >
          {busy ? "Saving" : isDone ? "Undo" : "Mark as handed in"}
        </button>
      </div>
    </article>
  );
}
