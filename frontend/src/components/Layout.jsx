import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";

const NAV = [
  { to: "/", label: "Overview", glyph: "◫", end: true },
  { to: "/ask", label: "Ask meetings", glyph: "⌕" },
  { to: "/meetings", label: "Meetings", glyph: "▤" },
  { to: "/decisions", label: "Decision log", glyph: "◎" },
  { to: "/actions", label: "Action items", glyph: "✓" },
];

const TITLES = {
  "/": "Overview",
  "/ask": "Ask your meetings",
  "/meetings": "Meetings",
  "/decisions": "Decision log",
  "/actions": "Action items",
  "/import": "Import transcript",
};

function BrandMark() {
  return (
    <span className="brand-mark" aria-hidden="true">
      <svg viewBox="0 0 32 32" fill="none">
        <path d="M7 24V10.5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2V24" />
        <path d="M11 8V5m10 3V5M7 14h18M11 18h4m-4 4h10" />
      </svg>
    </span>
  );
}

export default function Layout() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [health, setHealth] = useState(null);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth({ status: "down" }));
  }, []);

  useEffect(() => setMenuOpen(false), [location.pathname]);

  const title = TITLES[location.pathname] || "Meeting Intelligence";
  const initial = user?.username?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase() || "U";

  return (
    <div className="app-shell">
      <aside className={`sidebar ${menuOpen ? "sidebar-open" : ""}`}>
        <div className="sidebar-brand">
          <BrandMark />
          <div>
            <p className="brand-name">Meetwise</p>
            <p className="brand-caption">TRANSCRIPT INTELLIGENCE</p>
          </div>
        </div>

        <p className="sidebar-label">WORKSPACE</p>
        <nav className="sidebar-nav" aria-label="Main navigation">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => `nav-item ${isActive ? "nav-item-active" : ""}`}
            >
              <span className="nav-glyph" aria-hidden="true">{item.glyph}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <NavLink to="/import" className="sidebar-import">
            <span className="import-plus" aria-hidden="true">+</span>
            <span>Import a transcript</span>
          </NavLink>
          <div className="sidebar-health">
            <span className={`status-dot ${health?.status === "ok" ? "status-dot-ok" : ""}`} />
            <span>
              {health === null ? "Connecting to workspace" : health.status === "ok" ? "All systems operational" : "Backend unavailable"}
            </span>
          </div>
          {health?.status === "ok" && (
            <p className="sidebar-mode">
              {health.llm_mode === "llm" ? "AI answers enabled" : "Offline answer mode"}
            </p>
          )}
          {health?.status === "down" && (
            <p className="sidebar-mode sidebar-warning">Start the backend on port 8000 to reconnect.</p>
          )}
          <div className="account-row">
            <span className="avatar">{initial}</span>
            <span className="account-details">
              <span className="account-name" title={user?.username}>{user?.username}</span>
              <span className="account-email" title={user?.email}>{user?.email}</span>
            </span>
            <button
              type="button"
              className="signout-button"
              aria-label="Sign out"
              title="Sign out"
              onClick={async () => {
                try { await signOut(); } finally { navigate("/signin", { replace: true }); }
              }}
            >
              ↗
            </button>
          </div>
        </div>
      </aside>

      <div className="workspace">
        <header className="topbar">
          <button
            type="button"
            className="mobile-menu"
            aria-label={menuOpen ? "Close navigation" : "Open navigation"}
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((open) => !open)}
          >
            {menuOpen ? "×" : "☰"}
          </button>
          <div className="breadcrumb">
            <span>Workspace</span>
            <span className="breadcrumb-separator">/</span>
            <strong>{title}</strong>
          </div>
          <div className="topbar-right">
            <span className="topbar-badge"><span className="status-dot status-dot-ok" /> Private workspace</span>
            <span className="avatar avatar-small">{initial}</span>
          </div>
        </header>
        {menuOpen && <button className="mobile-scrim" aria-label="Close navigation" onClick={() => setMenuOpen(false)} />}
        <main className="page-content">
          <Outlet />
        </main>
        <footer className="app-footer">
          <span>Meetwise · Meeting Transcript Intelligence</span>
          <span>Private workspace · Your meetings stay yours</span>
        </footer>
      </div>
    </div>
  );
}
