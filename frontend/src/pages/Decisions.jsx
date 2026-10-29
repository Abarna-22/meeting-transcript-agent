import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, fmtDate } from "../api.js";

export default function Decisions() {
  const [items, setItems] = useState(null);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("");

  useEffect(() => {
    api.decisions().then(setItems).catch((e) => setError(e.message));
  }, []);

  const groups = useMemo(() => {
    const q = filter.trim().toLowerCase();
    const out = [];
    for (const d of items || []) {
      if (q && !d.text.toLowerCase().includes(q)) continue;
      const key = `${d.meeting_date}|${d.meeting_id}`;
      let g = out[out.length - 1];
      if (!g || g.key !== key) out.push((g = { key, date: d.meeting_date, id: d.meeting_id, title: d.meeting_title, list: [] }));
      g.list.push(d);
    }
    return out;
  }, [items, filter]);

  return (
    <div>
      <h1 className="h-page">Decision log</h1>
      <p className="mt-2 max-w-xl text-muted">
        Every decision across your meetings, oldest first, so you can see how a topic changed over time.
      </p>

      <div className="mt-6">
        <label htmlFor="f" className="sr-only">Filter decisions</label>
        <input id="f" className="field max-w-sm" placeholder="Filter, e.g. budget" value={filter} onChange={(e) => setFilter(e.target.value)} />
      </div>

      {error && <p className="mt-6 text-red-800">{error}</p>}
      {items === null && !error && <p className="mt-6 text-muted">Loading…</p>}
      {items && groups.length === 0 && <p className="mt-8 text-muted">{filter ? "No decisions match that filter." : "No decisions recorded yet."}</p>}

      <ol className="mt-8 border-l-2 border-line pl-6">
        {groups.map((g) => (
          <li key={g.key} className="relative pb-8 last:pb-0">
            <span className="absolute -left-[1.9rem] top-1.5 h-3 w-3 rounded-full border-2 border-spruce-800 bg-paper" aria-hidden />
            <p className="text-sm text-muted">{fmtDate(g.date)}</p>
            <Link to={`/meetings/${g.id}`} className="font-serif text-lg font-semibold text-spruce-900 hover:underline">{g.title}</Link>
            <ul className="mt-2 space-y-2">
              {g.list.map((d) => (
                <li key={d.id} className="rounded-lg border border-line bg-white px-4 py-3 text-sm leading-relaxed">
                  {d.text}
                  {d.timestamp && <span className="ml-2 text-xs text-muted">at {d.timestamp}</span>}
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ol>
    </div>
  );
}
