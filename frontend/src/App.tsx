import { Link, Route, Routes, useLocation } from "react-router-dom";

import AdminPage from "./pages/AdminPage";
import StudentPage from "./pages/StudentPage";
import TeacherPage from "./pages/TeacherPage";

const TODAY = new Intl.DateTimeFormat(undefined, {
  weekday: "short",
  day: "numeric",
  month: "short",
});

export default function App() {
  const path = useLocation().pathname;
  const onStaffSide = path.startsWith("/teacher") || path.startsWith("/admin");
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
          {path.startsWith("/teacher") ? (
            <Link className="ghost-btn" to="/admin">
              Admin &rarr;
            </Link>
          ) : null}
          <Link className="ghost-btn" to={onStaffSide ? "/" : "/teacher"}>
            {onStaffSide ? "Student view" : "Teacher view"} &rarr;
          </Link>
        </nav>
      </header>

      <Routes>
        <Route path="/" element={<StudentPage />} />
        <Route path="/teacher" element={<TeacherPage />} />
        <Route path="/admin" element={<AdminPage />} />
        <Route path="*" element={<StudentPage />} />
      </Routes>

      <footer className="footer">
        <span>Homework Diary</span>
        <span>{onStaffSide ? "Staff" : "Students"}</span>
      </footer>
    </div>
  );
}
