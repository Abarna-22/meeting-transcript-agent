import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, fmtDate } from "../api.js";

const TABS = ["Summary", "Action items", "Decisions", "Speakers", "Transcript"];

export default function MeetingDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const [m, setM] = useState(null);
  const [error, setError] = useState("");
  const [tab, setTab] = useState("Summary");

  useEffect(() => {
    api.meeting(id).then(setM).catch((e) => setError(e.message));
  }, [id]);

  async function remove() {
    if (!window.confirm(`Delete "${m.title}"? Its transcript and search index are removed.`)) return;
    await api.deleteMeeting(id);
    nav("/meetings");
  }

  async function toggle(item) {
    const status = item.status === "done" ? "open" : "done";
    await api.setActionStatus(item.id, status);
    setM({ ...m, action_items: m.action_items.map((a) => (a.id === item.id ? { ...a, status } : a)) });
  }

  if (error) return <p className="text-red-800">{error}</p>;
  if (!m) return <p className="text-muted">Loading…</p>;

  return (
    <div>
      <Link to="/meetings" className="text-sm text-muted hover:underline">All meetings</Link>
      <div className="mt-2 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="h-page">{m.title}</h1>
          <p className="mt-1 text-sm text-muted">
            {fmtDate(m.meeting_date)} · {m.word_count.toLocaleString()} words · {m.chunk_count} searchable chunks
          </p>
        </div>
        <button onClick={remove} className="btn-quiet text-red-800">Delete</button>
      </div>

      {m.insights_mode !== "llm" && (
        <p className="mt-4 rounded bg-amber-soft px-3 py-2 text-sm text-amber-deep">
          Summary, decisions and action items were found with keyword rules (offline mode). Add a GROQ_API_KEY and re-import for model-written notes.
        </p>
      )}

      <div role="tablist" className="mt-6 flex gap-1 overflow-x-auto border-b border-line">
        {TABS.map((t) => (
          <button
            key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)}
            className={`whitespace-nowrap border-b-2 px-4 py-2 text-sm ${
              tab === t ? "border-spruce-800 font-medium text-spruce-900" : "border-transparent text-muted hover:text-ink"
            }`}
          >
            {t}
            {t === "Action items" && ` (${m.action_items.length})`}
            {t === "Decisions" && ` (${m.decisions.length})`}
          </button>
        ))}
      </div>

      <div className="mt-6">
        {tab === "Summary" &&
          (m.summary.length ? (
            <ul className="space-y-3 font-serif text-lg leading-relaxed">
              {m.summary.map((s, i) => <li key={i} className="list-disc ml-5">{s}</li>)}
            </ul>
          ) : <p className="text-muted">No summary was generated for this meeting.</p>)}

        {tab === "Action items" &&
          (m.action_items.length ? (
            <ul className="divide-y divide-line rounded-lg border border-line bg-white">
              {m.action_items.map((a) => (
                <li key={a.id} className="flex items-start gap-3 p-4">
                  <input type="checkbox" className="mt-1 h-4 w-4 accent-spruce-800" checked={a.status === "done"} onChange={() => toggle(a)} aria-label={`Mark done: ${a.task}`} />
                  <div className={a.status === "done" ? "text-muted line-through" : ""}>
                    <p>{a.task}</p>
                    <p className="mt-1 text-sm text-muted">
                      {a.owner ? `Owner: ${a.owner}` : "No owner stated"}{a.due ? ` · Due: ${a.due}` : ""}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          ) : <p className="text-muted">No action items found.</p>)}

        {tab === "Decisions" &&
          (m.decisions.length ? (
            <ul className="divide-y divide-line rounded-lg border border-line bg-white">
              {m.decisions.map((d) => (
                <li key={d.id} className="p-4">
                  <p>{d.text}</p>
                  {d.timestamp && <p className="mt-1 text-sm text-muted">at {d.timestamp}</p>}
                </li>
              ))}
            </ul>
          ) : <p className="text-muted">No decisions found.</p>)}

        {tab === "Speakers" &&
          (m.participants.length ? (
            <div className="rounded-lg border border-line bg-white p-5">
              <ul className="space-y-4">
                {m.participants.map((p) => (
                  <li key={p.name}>
                    <div className="flex justify-between text-sm">
                      <span className="font-medium">{p.name}</span>
                      <span className="tabular-nums text-muted">{p.talk_time_pct}% · {p.turn_count} turns</span>
                    </div>
                    <div className="mt-1 h-2 rounded bg-paper" role="img" aria-label={`${p.name} spoke ${p.talk_time_pct} percent`}>
                      <div className="h-2 rounded bg-spruce-700" style={{ width: `${p.talk_time_pct}%` }} />
                    </div>
                  </li>
                ))}
              </ul>
              <p className="mt-4 text-xs text-muted">
                Share of talk time, estimated from {m.participants[0].basis === "time" ? "timestamps" : "word counts (this transcript has no timestamps)"}.
              </p>
            </div>
          ) : <p className="text-muted">This transcript has no speaker labels, so talk time can't be calculated.</p>)}

        {tab === "Transcript" && (
          <pre className="max-h-[32rem] overflow-auto whitespace-pre-wrap rounded-lg border border-line bg-white p-5 text-sm leading-relaxed">
            {m.raw_transcript}
          </pre>
        )}
      </div>
    </div>
  );
}
