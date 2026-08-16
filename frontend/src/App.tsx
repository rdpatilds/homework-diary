import { Link, Route, Routes, useLocation } from "react-router-dom";

import StudentPage from "./pages/StudentPage";
import TeacherPage from "./pages/TeacherPage";

export default function App() {
  const onTeacherSide = useLocation().pathname.startsWith("/teacher");
  return (
    <div className="page">
      <Routes>
        <Route path="/" element={<StudentPage />} />
        <Route path="/teacher" element={<TeacherPage />} />
        <Route path="*" element={<StudentPage />} />
      </Routes>
      <div className="footer">
        <span>Meridian School</span>
        {onTeacherSide ? (
          <Link to="/">Student view</Link>
        ) : (
          <Link to="/teacher">Teacher view</Link>
        )}
      </div>
    </div>
  );
}
