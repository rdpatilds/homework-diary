import { useState } from "react";
import type { FormEvent } from "react";

import { fetchDiary, handIn, takeBack } from "../api/client";
import type { Assignment, Student, StudentDiary } from "../api/types";
import { Field } from "../components/Field";
import { countdown, dueLabel, tierOf } from "../deadline";

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
    <main className="split">
      <section className="copy">
        <p className="crumbs">
          <span className="lead">Student</span>
          <span>&middot;</span>
          <span>No password</span>
          <span>&middot;</span>
          <span>Just your roll no.</span>
        </p>

        <h1>
          What you still owe,
          <br />
          <em>and when.</em>
        </h1>

        <p className="lede">
          Enter your details and we'll open your diary. Your{" "}
          <strong>class and section</strong> decide what you see, and your{" "}
          <strong>roll number</strong> remembers what you've handed in.
        </p>
        <p className="aside">Everything in one page. Not five group chats.</p>

        <ul className="legend">
          <li>
            <span className="head">
              <i className="dot crit" />
              Missed
            </span>
            <p>Past the deadline. Sits at the top.</p>
          </li>
          <li>
            <span className="head">
              <i className="dot med" />
              To do
            </span>
            <p>Still open. Soonest deadline first.</p>
          </li>
          <li>
            <span className="head">
              <i className="dot low" />
              Handed in
            </span>
            <p>Marked done. Undo before the deadline.</p>
          </li>
        </ul>
      </section>

      <form className="panel" onSubmit={open}>
        <div className="panel-head">
          <h2>Open your diary</h2>
          <span className="tag">Student</span>
        </div>
        <div className="form-body">
          <Field label="Name" value={details.studentName}
            onChange={(studentName) => setDetails({ ...details, studentName })}
            autoComplete="name" placeholder="Priya Raman" />

          <div className="row-2">
            <Field label="Roll no." data value={details.rollNo}
              onChange={(rollNo) => setDetails({ ...details, rollNo })}
              inputMode="numeric" placeholder="24" />
            <div className="row-2">
              <Field label="Class" data value={details.className}
                onChange={(className) => setDetails({ ...details, className })}
                placeholder="8" />
              <Field label="Section" data value={details.section}
                onChange={(section) => setDetails({ ...details, section })}
                placeholder="A" />
            </div>
          </div>

          <div className="submit-row">
            <button type="submit" className="primary" disabled={busy}>
              {busy ? "Opening" : "Open my diary"}
            </button>
            <span className="hint">Nothing is saved to this device</span>
          </div>

          {screen.kind === "identify" && screen.error ? (
            <p className="toast" role="alert">
              {screen.error}
            </p>
          ) : null}
        </div>
      </form>
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
  const owing = missed.length + todo.length;
  const soonest = todo[0];

  const rows = (items: Assignment[]) => (
    <ul className="rows actionable">
      {items.map((item) => {
        const left = countdown(item.dueAt, at);
        const state = item.status.state;
        const tier = tierOf(state, left.urgency);
        const isDone = state === "done";
        return (
          <li key={item.id}>
            <span className="cell-subject">
              <i className={`dot ${tier}`} />
              {item.subject}
            </span>
            <span className="cell-title">
              <span className={isDone ? "name settled" : "name"}>{item.title}</span>
              {item.details && !isDone ? <p className="brief">{item.details}</p> : null}
            </span>
            <span className="cell-due">Due {dueLabel(item.dueAt)}</span>
            <span className={`chip ${tier}`}>
              {isDone ? "handed in" : `${left.short} ${state === "missed" ? "late" : "left"}`}
            </span>
            <button type="button" className="link" disabled={screen.busy === item.id}
              onClick={() => onToggle(item)}>
              {screen.busy === item.id ? "Saving" : isDone ? "Undo" : "Mark done"}
            </button>
          </li>
        );
      })}
    </ul>
  );

  return (
    <>
      <main className="split">
        <section className="copy">
          <p className="crumbs">
            <span className="lead">Student</span>
            <span>&middot;</span>
            <span>
              Class {student.className}-{student.section}
            </span>
            <span>&middot;</span>
            <span>Roll {student.rollNo}</span>
          </p>

          <h1>
            {owing === 0 ? "You're all clear," : "Still to do,"}
            <br />
            <em>{student.studentName}.</em>
          </h1>

          <p className="lede">
            {owing === 0
              ? "Nothing is open for your class right now. Check back after your next lesson."
              : "Soonest deadline first. Mark something done and it moves to the bottom, where you can undo it."}
          </p>

          <ul className="stats">
            <li>
              <span className="label">To do</span>
              <span className="value">{todo.length}</span>
            </li>
            <li>
              <span className="label">Next due</span>
              <span className="value warn">
                {soonest ? countdown(soonest.dueAt, at).short : "—"}
              </span>
            </li>
            <li>
              <span className="label">Missed</span>
              <span className={missed.length > 0 ? "value bad" : "value"}>
                {missed.length}
              </span>
            </li>
          </ul>
        </section>

        <section className="panel">
          <div className="panel-head">
            <h2>Your diary</h2>
            <button type="button" className="link" onClick={onChangeStudent}>
              Not you?
            </button>
          </div>
          <div className="form-body">
            <p className="lede" style={{ margin: 0 }}>
              Signed in as <strong>{student.studentName}</strong>, roll{" "}
              <strong>{student.rollNo}</strong>, class{" "}
              <strong>
                {student.className}-{student.section}
              </strong>
              .
            </p>
            <div className="progress">
              <div className="progress-head">
                <span className="label">Handed in</span>
                <span className="ratio">
                  {done.length} of {assignments.length}
                </span>
              </div>
              <div className="track">
                <div
                  className="fill"
                  style={{
                    width: assignments.length
                      ? `${(done.length / assignments.length) * 100}%`
                      : "0%",
                  }}
                />
              </div>
            </div>
            {screen.error ? (
              <p className="toast" role="alert">
                {screen.error}
              </p>
            ) : null}
          </div>
        </section>
      </main>

      <div className="board">
        {missed.length > 0 ? (
          <section className="panel">
            <div className="panel-head">
              <p className="strip">Past the deadline &middot; {missed.length}</p>
              <p className="panel-note">Hand these in as soon as you can.</p>
            </div>
            {rows(missed)}
          </section>
        ) : null}

        {todo.length > 0 ? (
          <section className="panel">
            <div className="panel-head">
              <p className="strip">Still to do &middot; {todo.length}</p>
              <p className="panel-note">Soonest deadline first.</p>
            </div>
            {rows(todo)}
          </section>
        ) : null}

        {owing === 0 ? (
          <section className="panel">
            <div className="blank">
              <h3>Nothing is due.</h3>
              <p>
                No open homework for class {student.className}-{student.section}.
              </p>
            </div>
          </section>
        ) : null}

        {done.length > 0 ? (
          <section className="panel">
            <div className="panel-head">
              <p className="strip">Handed in &middot; {done.length}</p>
              <p className="panel-note">Undo any of these before the deadline passes.</p>
            </div>
            {rows(done)}
          </section>
        ) : null}
      </div>
    </>
  );
}
