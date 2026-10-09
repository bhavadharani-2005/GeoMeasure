import { FolderOpen, LayoutGrid, Menu, UploadCloud, X } from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { filesApi } from "../../api/files";
import { useAsync } from "../../hooks/useAsync";

const NAV = [
  { to: "/", label: "Overview", icon: LayoutGrid, end: true },
  { to: "/upload", label: "Upload", icon: UploadCloud, end: false },
  { to: "/files", label: "Files", icon: FolderOpen, end: false },
];

const HEALTH_POLL_MS = 30_000;

function ApiStatus() {
  const { data, error, loading, reload } = useAsync(() => filesApi.health(), []);
  useEffect(() => {
    const timer = setInterval(reload, HEALTH_POLL_MS);
    return () => clearInterval(timer);
  }, [reload]);

  const state = loading && !data && !error ? "checking" : error || data?.status !== "ok" ? "down" : "up";
  const label = { checking: "Checking API…", up: "API online", down: "API unreachable" }[state];
  return (
    <div className="api-status" role="status">
      <span className={`api-status__dot api-status__dot--${state}`} aria-hidden="true" />
      <div>
        <div className="api-status__label">{label}</div>
        {data && <div className="api-status__meta">v{data.version}</div>}
      </div>
    </div>
  );
}

export function AppLayout() {
  const [open, setOpen] = useState(false);
  const location = useLocation();
  useEffect(() => setOpen(false), [location.pathname]);

  return (
    <div className="shell">
      <div className="topbar">
        <button
          type="button"
          className="btn btn--ghost btn--icon"
          aria-label={open ? "Close navigation" : "Open navigation"}
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
        >
          {open ? <X size={20} /> : <Menu size={20} />}
        </button>
        <span className="brand__name">GeoMeasure</span>
      </div>

      <aside className={`sidebar${open ? " sidebar--open" : ""}`}>
        <div className="brand">
          <img src="/favicon.svg" alt="" width={28} height={28} />
          <div>
            <div className="brand__name">GeoMeasure</div>
            <div className="brand__tag">Spatial files. Reliable measurements.</div>
          </div>
        </div>
        <nav className="nav" aria-label="Main">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} className="nav__link">
              <Icon size={18} aria-hidden="true" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar__footer">
          <ApiStatus />
        </div>
      </aside>
      {open && <div className="scrim" onClick={() => setOpen(false)} aria-hidden="true" />}

      <main className="workspace">
        <Outlet />
      </main>
    </div>
  );
}
