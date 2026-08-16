import { useState } from "react";
import type { FormEvent } from "react";

import { fetchDiary, handIn, takeBack } from "../api/client";
import type { Assignment, Student, StudentDiary } from "../api/types";
import { CurveField } from "../components/CurveField";
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
    <section className="hero">
      <CurveField tone="green" />
      <div className="hero-inner split">
        <div className="hero-copy">
          <p className="badge">
            No password needed <b>just your roll no.</b>
          </p>
          <h1>
            What you still owe,
            <br />
            <em>and when.</em>
          </h1>
          <p className="lede">
            Enter your details and we'll open your diary. Your <b>class</b> and{" "}
            <b>section</b> decide what you see.
          </p>
        </div>

        <form className="panel cover" onSubmit={open}>
          <div className="panel-head c6">
            <h2>Open your diary</h2>
            <p className="eyebrow">Student</p>
          </div>
          <Field label="Name" span={6} value={details.studentName}
            onChange={(studentName) => setDetails({ ...details, studentName })}
            autoComplete="name" placeholder="Priya Raman" />
          <Field label="Roll no." span={6} value={details.rollNo}
            onChange={(rollNo) => setDetails({ ...details, rollNo })}
            inputMode="numeric" placeholder="24" />
          <Field label="Class" value={details.className}
            onChange={(className) => setDetails({ ...details, className })}
            placeholder="8" />
          <Field label="Section" value={details.section}
            onChange={(section) => setDetails({ ...details, section })}
            placeholder="A" />
          <div className="actions">
            <button type="submit" disabled={busy}>
              {busy ? "Opening" : "Open my diary"}
            </button>
          </div>
          {screen.kind === "identify" && screen.error ? (
            <p className="notice c6" role="alert">
              {screen.error}
            </p>
          ) : null}
        </form>

        {/* Last in source so a phone reaches the form before the sample. On a
            wide screen the grid lifts it under the copy. */}
        <Preview />
      </div>
    </section>
  );
}

/** A still of what waits on the other side of the form. */
function Preview() {
  const rows = [
    { subject: "Maths", title: "Algebra worksheet", when: "2 days late", tone: "missed" },
    { subject: "Science", title: "Photosynthesis lab write-up", when: "2 days left", tone: "open" },
    { subject: "English", title: "Letter to the editor", when: "handed in", tone: "done" },
  ] as const;
  return (
    <div className="preview" aria-hidden="true">
      {rows.map((row) => (
        <div className="preview-row" key={row.title}>
          <span>
            <i className={`dot ${row.tone}`} />
            <span className="title">{row.title}</span>
          </span>
          <span className="when">{row.when}</span>
        </div>
      ))}
    </div>
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
  const owing = missed.length + todo.length;

  const cards = (items: Assignment[]) => (
    <div className="cards">
      {items.map((item, index) => (
        <Card
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
    <>
      <section className="hero">
        <CurveField tone="green" />
        <div className="hero-inner">
          <div>
            <p className={missed.length > 0 ? "badge alarm" : "badge"}>
              Class {student.className}-{student.section} &middot; Roll {student.rollNo}{" "}
              <b>{missed.length > 0 ? `${missed.length} missed` : "all on time"}</b>
            </p>
            <h1>
              {owing === 0 ? "You're all clear," : "Still to do,"}
              <br />
              <em>{student.studentName}.</em>
            </h1>
            <ul className="tally">
              <li>
                <i className="dot open" />
                {todo.length} to do
              </li>
              {missed.length > 0 ? (
                <li>
                  <i className="dot missed" />
                  {missed.length} missed
                </li>
              ) : null}
              {done.length > 0 ? (
                <li>
                  <i className="dot done" />
                  {done.length} handed in
                </li>
              ) : null}
              <li>
                <button type="button" className="link" onClick={onChangeStudent}>
                  Not you?
                </button>
              </li>
            </ul>
          </div>
        </div>
      </section>

      <div className="board">
        {screen.error ? (
          <p className="notice" role="alert">
            {screen.error}
          </p>
        ) : null}

        {missed.length > 0 ? (
          <section className="section">
            <div className="section-head">
              <h2>Past the deadline</h2>
              <span className="rule" />
            </div>
            {cards(missed)}
          </section>
        ) : null}

        {todo.length > 0 ? (
          <section className="section">
            <div className="section-head">
              <h2>Still to do</h2>
              <span className="rule" />
            </div>
            {cards(todo)}
          </section>
        ) : null}

        {owing === 0 ? (
          <div className="empty">
            <h2>Nothing is due.</h2>
            <p>
              No open homework for class {student.className}-{student.section}. Check
              back after your next lesson.
            </p>
          </div>
        ) : null}

        {done.length > 0 ? (
          <section className="section">
            <div className="section-head">
              <h2>Handed in</h2>
              <span className="rule" />
            </div>
            {cards(done)}
          </section>
        ) : null}
      </div>
    </>
  );
}

function Card({
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
  const state = item.status.state;
  const isDone = state === "done";
  const shell = isDone ? "card settled" : state === "missed" ? "card overdue" : "card";
  return (
    <article className={shell} style={{ animationDelay: `${index * 55}ms` }}>
      <div className="card-top">
        <span className="subject">
          <i className={`dot ${state}`} />
          {item.subject}
        </span>
        {isDone ? (
          <span className="count done">handed in</span>
        ) : (
          <span className={`count ${left.urgency}`}>
            <b>{left.value}</b> {left.unit} {state === "missed" ? "late" : "left"}
          </span>
        )}
      </div>
      <h3>{item.title}</h3>
      {item.details && !isDone ? <p>{item.details}</p> : null}
      <p className="meta">
        Due {dueLabel(item.dueAt)} &middot; {item.assignedBy}
      </p>
      <div className="card-foot">
        <button type="button" className="link" disabled={busy} onClick={() => onToggle(item)}>
          {busy ? "Saving" : isDone ? "Undo" : "Mark as handed in"}
        </button>
      </div>
    </article>
  );
}
