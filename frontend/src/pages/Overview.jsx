import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, fmtDate } from "../api.js";

function MetricCard({ label, value, note, icon, tone }) {
  return (
    <article className="metric-card">
      <div className={`metric-icon metric-icon-${tone}`} aria-hidden="true">{icon}</div>
      <p className="metric-label">{label}</p>
      <div className="metric-value">{value}</div>
      <p className="metric-note">{note}</p>
    </article>
  );
}

function LoadingRows() {
  return (
    <div className="space-y-3" aria-label="Loading workspace data">
      {[0, 1, 2].map((item) => <div key={item} className="skeleton-row" />)}
    </div>
  );
}

export default function Overview() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    Promise.all([
      api.meetings(),
      api.decisions(),
      api.actionItems({ status: "open" }),
      api.actionItems({ status: "done" }),
    ])
      .then(([meetings, decisions, openActions, completedActions]) => {
        if (active) setData({ meetings, decisions, openActions, completedActions });
      })
      .catch((err) => { if (active) setError(err.message); });
    return () => { active = false; };
  }, []);

  const recentMeetings = useMemo(() => (data?.meetings || []).slice(0, 4), [data]);
  const latestSummary = recentMeetings.find((meeting) => meeting.summary?.length)?.summary?.[0];
  const completionRate = data
    ? data.openActions.length + data.completedActions.length === 0
      ? 0
      : Math.round((data.completedActions.length / (data.openActions.length + data.completedActions.length)) * 100)
    : 0;

  return (
    <div className="page-stack">
      <section className="welcome-panel">
        <div className="welcome-copy">
          <p className="eyebrow"><span className="eyebrow-line" /> YOUR MEETING WORKSPACE</p>
          <h1 className="welcome-title">Turn conversations into <em>clear next steps.</em></h1>
          <p className="welcome-description">
            Your meeting notes, decisions, and follow-ups—organized in one searchable workspace.
          </p>
          <div className="welcome-actions">
            <Link to="/ask" className="button button-light">
              <span aria-hidden="true">⌕</span> Ask your meetings
            </Link>
            <Link to="/import" className="button button-outline">
              <span aria-hidden="true">+</span> Import transcript
            </Link>
          </div>
        </div>
        <div className="welcome-art" aria-hidden="true">
          <div className="art-orbit orbit-one" />
          <div className="art-orbit orbit-two" />
          <div className="art-document">
            <span className="art-document-top" />
            <span className="art-document-line" />
            <span className="art-document-line short" />
            <span className="art-document-quote">“</span>
            <span className="art-document-line" />
            <span className="art-document-line medium" />
          </div>
          <span className="art-spark spark-one">✦</span>
          <span className="art-spark spark-two">✦</span>
          <span className="art-pill">ideas → impact</span>
        </div>
      </section>

      {error && (
        <div role="alert" className="feedback-error">
          <strong>Couldn’t load your workspace.</strong> {error}
          <button type="button" className="text-link" onClick={() => window.location.reload()}>Try again</button>
        </div>
      )}

      <section aria-labelledby="snapshot-heading">
        <div className="section-heading">
          <div>
            <p className="eyebrow">AT A GLANCE</p>
            <h2 id="snapshot-heading" className="section-title">Workspace snapshot</h2>
          </div>
          <span className="data-caption">{data ? "Live from your meetings" : "Loading your data…"}</span>
        </div>
        <div className="metrics-grid">
          <MetricCard label="Meetings" value={data?.meetings.length ?? "—"} note="Transcripts in your library" icon="▤" tone="green" />
          <MetricCard label="Decisions" value={data?.decisions.length ?? "—"} note="Agreements captured" icon="◎" tone="gold" />
          <MetricCard label="Open action items" value={data?.openActions.length ?? "—"} note="Next steps to follow up" icon="↗" tone="blue" />
          <MetricCard label="Completion rate" value={data ? `${completionRate}%` : "—"} note={`${data?.completedActions.length ?? 0} tasks completed`} icon="✓" tone="rose" />
        </div>
      </section>

      <div className="overview-columns">
        <section className="panel recent-panel" aria-labelledby="recent-heading">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">YOUR LIBRARY</p>
              <h2 id="recent-heading" className="section-title">Recent meetings</h2>
            </div>
            <Link to="/meetings" className="text-link">View all <span aria-hidden="true">→</span></Link>
          </div>

          {!data && !error ? <LoadingRows /> : null}
          {data?.meetings.length === 0 && (
            <div className="empty-state">
              <span className="empty-state-icon" aria-hidden="true">▤</span>
              <h3>Your library starts here</h3>
              <p>Import a transcript to get an instant summary, decisions, and searchable answers.</p>
              <Link to="/import" className="text-link">Import your first meeting →</Link>
            </div>
          )}
          {recentMeetings.length > 0 && (
            <ul className="recent-list">
              {recentMeetings.map((meeting) => (
                <li key={meeting.id}>
                  <Link to={`/meetings/${meeting.id}`} className="recent-meeting">
                    <span className="meeting-file-icon" aria-hidden="true">▤</span>
                    <span className="recent-meeting-main">
                      <strong>{meeting.title}</strong>
                      <span>{fmtDate(meeting.meeting_date)} <span className="metadata-dot">·</span> {meeting.word_count.toLocaleString()} words</span>
                    </span>
                    <span className="recent-meeting-count">{meeting.action_item_count} tasks</span>
                    <span className="recent-arrow" aria-hidden="true">→</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>

        <aside className="overview-side">
          <section className="panel progress-panel" aria-labelledby="progress-heading">
            <p className="eyebrow">FOLLOW-THROUGH</p>
            <h2 id="progress-heading" className="section-title">Action progress</h2>
            {!data && !error ? <div className="skeleton-row mt-5" /> : null}
            {data && (
              <>
                <div className="progress-summary">
                  <span className="progress-number">{completionRate}<small>%</small></span>
                  <span className="progress-caption">of tasks<br />completed</span>
                </div>
                <div className="progress-track" role="progressbar" aria-label="Action item completion rate" aria-valuenow={completionRate} aria-valuemin="0" aria-valuemax="100">
                  <span style={{ width: `${completionRate}%` }} />
                </div>
                <div className="progress-legend">
                  <span><i className="legend-dot legend-done" />{data.completedActions.length} done</span>
                  <span><i className="legend-dot legend-open" />{data.openActions.length} open</span>
                </div>
                <Link to="/actions" className="button button-dark button-full">Review action items <span aria-hidden="true">→</span></Link>
              </>
            )}
          </section>

          <section className="insight-card" aria-labelledby="insight-heading">
            <div className="insight-top">
              <span className="insight-spark" aria-hidden="true">✦</span>
              <span className="insight-label">MEETING INSIGHT</span>
            </div>
            <h2 id="insight-heading">A little clarity goes a long way.</h2>
            <p>{latestSummary || "Import a transcript and let your workspace surface the ideas, decisions, and commitments that matter."}</p>
            {recentMeetings[0] && <Link to={`/meetings/${recentMeetings[0].id}`}>Explore latest meeting <span aria-hidden="true">→</span></Link>}
          </section>
        </aside>
      </div>

      <section className="feature-strip" aria-label="Workspace features">
        <div><span aria-hidden="true">⌕</span><strong>Ask naturally</strong><small>Get answers with meeting citations</small></div>
        <div><span aria-hidden="true">◎</span><strong>Track decisions</strong><small>See how agreements evolve</small></div>
        <div><span aria-hidden="true">✓</span><strong>Keep momentum</strong><small>Turn commitments into action</small></div>
      </section>
    </div>
  );
}
