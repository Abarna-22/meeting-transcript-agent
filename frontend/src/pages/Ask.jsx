import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, fmtDate } from "../api.js";
import CitedAnswer from "../components/CitedAnswer.jsx";

const EXAMPLES = [
  "What did we decide about the budget?",
  "Why was the beta date moved?",
  "What did Sarah commit to?",
];

export default function Ask() {
  const [meetings, setMeetings] = useState(null);
  const [question, setQuestion] = useState("");
  const [scope, setScope] = useState("");
  const [state, setState] = useState({ status: "idle" });

  useEffect(() => {
    api.meetings().then(setMeetings).catch(() => setMeetings([]));
  }, []);

  async function ask(q = question) {
    const text = q.trim();
    if (text.length < 3) return;
    setQuestion(text);
    setState({ status: "loading" });
    try {
      const result = await api.query({ question: text, meeting_id: scope ? Number(scope) : null });
      setState({ status: "done", result });
    } catch (e) {
      setState({ status: "error", message: e.message });
    }
  }

  const empty = meetings && meetings.length === 0;

  return (
    <div>
      <h1 className="h-page">Ask your meetings</h1>
      <p className="mt-2 max-w-xl text-muted">
        Ask in plain English. Every answer links back to the meeting and moment it came from.
      </p>

      {empty ? (
        <div className="mt-8 rounded-lg border border-dashed border-line bg-white p-8">
          <p className="font-serif text-lg">No meetings yet.</p>
          <p className="mt-1 text-sm text-muted">Import a transcript (.txt, .vtt or .srt) and you can start asking questions.</p>
          <Link to="/import" className="btn-primary mt-4">Import a transcript</Link>
        </div>
      ) : (
        <form
          className="mt-8"
          onSubmit={(e) => {
            e.preventDefault();
            ask();
          }}
        >
          <label htmlFor="q" className="sr-only">Your question</label>
          <textarea
            id="q"
            rows={3}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) ask();
            }}
            placeholder="What was decided about the Q3 budget?"
            className="field resize-y font-serif text-lg"
          />
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <label htmlFor="scope" className="text-sm text-muted">Search in</label>
            <select id="scope" value={scope} onChange={(e) => setScope(e.target.value)} className="field w-auto max-w-[16rem]">
              <option value="">All meetings</option>
              {(meetings || []).map((m) => (
                <option key={m.id} value={m.id}>{m.title} · {fmtDate(m.meeting_date)}</option>
              ))}
            </select>
            <button type="submit" className="btn-primary ml-auto" disabled={state.status === "loading" || question.trim().length < 3}>
              {state.status === "loading" ? "Searching…" : "Ask"}
            </button>
          </div>
          {state.status === "idle" && (
            <div className="mt-5 flex flex-wrap gap-2">
              {EXAMPLES.map((ex) => (
                <button key={ex} type="button" onClick={() => ask(ex)} className="btn-quiet !py-1.5 text-muted">
                  {ex}
                </button>
              ))}
            </div>
          )}
        </form>
      )}

      <div className="mt-10" aria-live="polite">
        {state.status === "loading" && <p className="text-muted">Reading your meetings…</p>}
        {state.status === "error" && (
          <p className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
            {state.message}. Check that the backend is running and try again.
          </p>
        )}
        {state.status === "done" && <CitedAnswer result={state.result} />}
      </div>
    </div>
  );
}
