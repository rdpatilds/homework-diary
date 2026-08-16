import { Link, Route, Routes, useLocation } from "react-router-dom";

import StudentPage from "./pages/StudentPage";
import TeacherPage from "./pages/TeacherPage";

export default function App() {
  const onTeacherSide = useLocation().pathname.startsWith("/teacher");
  return (
    <div className={onTeacherSide ? "shell teacher" : "shell"}>
      <header className="topbar">
        <Link to="/" className="brand">
          <span className="brand-mark" aria-hidden="true" />
          Meridian School
        </Link>
        <nav>
          {onTeacherSide ? (
            <Link className="pill-link" to="/">
              Student view
            </Link>
          ) : (
            <Link className="pill-link" to="/teacher">
              Teacher view
            </Link>
          )}
        </nav>
      </header>

      <Routes>
        <Route path="/" element={<StudentPage />} />
        <Route path="/teacher" element={<TeacherPage />} />
        <Route path="*" element={<StudentPage />} />
      </Routes>

      <footer className="footer">
        <span>Homework diary</span>
        <span>{onTeacherSide ? "Staff" : "Students"}</span>
      </footer>
    </div>
  );
}
