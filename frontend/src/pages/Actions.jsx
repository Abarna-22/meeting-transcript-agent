import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, fmtDate } from "../api.js";

export default function Actions() {
  const [items, setItems] = useState(null);
  const [error, setError] = useState("");
  const [owner, setOwner] = useState("");
  const [status, setStatus] = useState("open");

  useEffect(() => {
    const params = {};
    if (owner.trim()) params.owner = owner.trim();
    if (status) params.status = status;
    const t = setTimeout(() => api.actionItems(params).then(setItems).catch((e) => setError(e.message)), 200);
    return () => clearTimeout(t);
  }, [owner, status]);

  async function toggle(item) {
    const next = item.status === "done" ? "open" : "done";
    await api.setActionStatus(item.id, next);
    setItems((cur) => (status ? cur.filter((a) => a.id !== item.id) : cur.map((a) => (a.id === item.id ? { ...a, status: next } : a))));
  }

  return (
    <div>
      <h1 className="h-page">Action items</h1>
      <p className="mt-2 max-w-xl text-muted">Tasks pulled out of every meeting. Tick them off as they get done.</p>

      <div className="mt-6 flex flex-wrap gap-3">
        <div>
          <label htmlFor="o" className="sr-only">Owner</label>
          <input id="o" className="field w-56" placeholder="Filter by owner, e.g. Arun" value={owner} onChange={(e) => setOwner(e.target.value)} />
        </div>
        <div>
          <label htmlFor="s" className="sr-only">Status</label>
          <select id="s" className="field w-auto" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="open">Open</option>
            <option value="done">Done</option>
            <option value="">All</option>
          </select>
        </div>
      </div>

      {error && <p className="mt-6 text-red-800">{error}</p>}
      {items === null && !error && <p className="mt-6 text-muted">Loading…</p>}
      {items?.length === 0 && <p className="mt-8 text-muted">Nothing here. Change the filters or import more meetings.</p>}

      {items?.length > 0 && (
        <ul className="mt-6 divide-y divide-line rounded-lg border border-line bg-white">
          {items.map((a) => (
            <li key={a.id} className="flex items-start gap-3 p-4">
              <input type="checkbox" className="mt-1 h-4 w-4 accent-spruce-800" checked={a.status === "done"} onChange={() => toggle(a)} aria-label={`Mark done: ${a.task}`} />
              <div className={a.status === "done" ? "text-muted line-through" : ""}>
                <p>{a.task}</p>
                <p className="mt-1 text-sm text-muted">
                  {a.owner || "No owner stated"}{a.due ? ` · due ${a.due}` : ""} ·{" "}
                  <Link to={`/meetings/${a.meeting_id}`} className="underline">{a.meeting_title}</Link>, {fmtDate(a.meeting_date)}
                </p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
