import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, fmtDate } from "../api.js";

const PLATFORM = { upload: "Upload", zoom: "Zoom", teams: "Teams", meet: "Google Meet", otter: "Otter.ai" };

export default function Meetings() {
  const [meetings, setMeetings] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.meetings().then(setMeetings).catch((e) => setError(e.message));
  }, []);

  return (
    <div>
      <div className="flex items-end justify-between gap-4">
        <h1 className="h-page">Meetings</h1>
        <Link to="/import" className="btn-primary">Import transcript</Link>
      </div>

      {error && <p className="mt-6 text-sm text-red-800">{error}</p>}
      {meetings === null && !error && <p className="mt-6 text-muted">Loading…</p>}
      {meetings?.length === 0 && (
        <p className="mt-8 rounded-lg border border-dashed border-line bg-white p-8 text-muted">
          No meetings yet. Import your first transcript to get summaries, action items and searchable answers.
        </p>
      )}

      {meetings?.length > 0 && (
        <div className="mt-8 overflow-x-auto rounded-lg border border-line bg-white">
          <table className="w-full min-w-[34rem] text-left text-sm">
            <thead className="border-b border-line text-muted">
              <tr>
                <th className="px-4 py-3 font-medium">Meeting</th>
                <th className="px-4 py-3 font-medium">Date</th>
                <th className="px-4 py-3 font-medium">Source</th>
                <th className="px-4 py-3 text-right font-medium">Decisions</th>
                <th className="px-4 py-3 text-right font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {meetings.map((m) => (
                <tr key={m.id} className="border-b border-line last:border-0 hover:bg-paper">
                  <td className="px-4 py-3">
                    <Link to={`/meetings/${m.id}`} className="font-medium text-spruce-800 hover:underline">{m.title}</Link>
                    <p className="text-xs text-muted">{m.word_count.toLocaleString()} words</p>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3">{fmtDate(m.meeting_date)}</td>
                  <td className="px-4 py-3">{PLATFORM[m.platform] || m.platform}</td>
                  <td className="px-4 py-3 text-right tabular-nums">{m.decision_count}</td>
                  <td className="px-4 py-3 text-right tabular-nums">{m.action_item_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
