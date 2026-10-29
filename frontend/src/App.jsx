import { Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./auth.jsx";
import Layout from "./components/Layout.jsx";
import Auth from "./pages/Auth.jsx";
import Overview from "./pages/Overview.jsx";
import Ask from "./pages/Ask.jsx";
import Meetings from "./pages/Meetings.jsx";
import MeetingDetail from "./pages/MeetingDetail.jsx";
import Decisions from "./pages/Decisions.jsx";
import Actions from "./pages/Actions.jsx";
import Import from "./pages/Import.jsx";

function RequireAuth() {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <p className="p-8 text-center text-muted">Loading…</p>;
  return user ? <Outlet /> : <Navigate to="/signin" replace state={{ from: location }} />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/signin" element={<Auth mode="signin" />} />
      <Route path="/signup" element={<Auth mode="signup" />} />
      <Route element={<RequireAuth />}>
        <Route element={<Layout />}>
          <Route index element={<Overview />} />
          <Route path="ask" element={<Ask />} />
          <Route path="meetings" element={<Meetings />} />
          <Route path="meetings/:id" element={<MeetingDetail />} />
          <Route path="decisions" element={<Decisions />} />
          <Route path="actions" element={<Actions />} />
          <Route path="import" element={<Import />} />
          <Route path="*" element={<p className="p-10 text-muted">Page not found.</p>} />
        </Route>
      </Route>
    </Routes>
  );
}
