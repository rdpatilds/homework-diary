import { Link, Route, Routes, useLocation } from "react-router-dom";

import StudentPage from "./pages/StudentPage";
import TeacherPage from "./pages/TeacherPage";

const TODAY = new Intl.DateTimeFormat(undefined, {
  weekday: "short",
  day: "numeric",
  month: "short",
});

export default function App() {
  const onTeacherSide = useLocation().pathname.startsWith("/teacher");
  return (
    <div className="shell">
      <header className="topbar">
        <Link to="/" className="brand">
          <span className="brand-mark" aria-hidden="true" />
          <span className="brand-name">Meridian School</span>
          <span className="brand-tag">Homework Diary</span>
        </Link>
        <nav>
          <span className="stamp">
            <i aria-hidden="true" />
            {TODAY.format(new Date())}
          </span>
          <Link className="ghost-btn" to={onTeacherSide ? "/" : "/teacher"}>
            {onTeacherSide ? "Student view" : "Teacher view"} &rarr;
          </Link>
        </nav>
      </header>

      <Routes>
        <Route path="/" element={<StudentPage />} />
        <Route path="/teacher" element={<TeacherPage />} />
        <Route path="*" element={<StudentPage />} />
      </Routes>

      <footer className="footer">
        <span>Homework Diary</span>
        <span>{onTeacherSide ? "Staff" : "Students"}</span>
      </footer>
    </div>
  );
}
