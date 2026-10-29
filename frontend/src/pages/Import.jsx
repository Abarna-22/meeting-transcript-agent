import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";

export default function Import() {
  const nav = useNavigate();
  const fileRef = useRef(null);
  const [file, setFile] = useState(null);
  const [text, setText] = useState("");
  const [title, setTitle] = useState("");
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [platform, setPlatform] = useState("upload");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(e) {
    e.preventDefault();
    setError("");
    if (!file && !text.trim()) return setError("Choose a transcript file or paste the transcript text.");
    const fd = new FormData();
    if (file) fd.append("file", file);
    else fd.append("text", text);
    if (title.trim()) fd.append("title", title.trim());
    fd.append("meeting_date", date);
    fd.append("platform", platform);
    setBusy(true);
    try {
      const m = await api.createMeeting(fd);
      nav(`/meetings/${m.id}`);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <div>
      <h1 className="h-page">Import a transcript</h1>
      <p className="mt-2 max-w-xl text-muted">
        Zoom, Teams and Meet exports (.vtt, .srt) and plain .txt files work. Speakers and timestamps are picked up when present.
      </p>

      <form onSubmit={submit} className="mt-8 space-y-6">
        <div>
          <span className="mb-2 block text-sm font-medium">Transcript file</span>
          <div className="flex items-center gap-3 rounded-lg border border-dashed border-line bg-white p-4">
            <button type="button" className="btn-quiet" onClick={() => fileRef.current?.click()}>Choose file</button>
            <span className="truncate text-sm text-muted">{file ? file.name : "No file chosen"}</span>
            {file && (
              <button type="button" className="ml-auto text-sm text-muted underline" onClick={() => { setFile(null); fileRef.current.value = ""; }}>
                Remove
              </button>
            )}
            <input ref={fileRef} type="file" accept=".txt,.vtt,.srt" className="sr-only" onChange={(e) => setFile(e.target.files[0] || null)} />
          </div>
        </div>

        <div>
          <label htmlFor="paste" className="mb-2 block text-sm font-medium">Or paste the transcript</label>
          <textarea
            id="paste" rows={8} value={text} disabled={!!file}
            onChange={(e) => setText(e.target.value)}
            placeholder={"Raj: Let's lock the budget today.\nSarah: I'll share the test plan by Monday."}
            className="field font-mono disabled:opacity-50"
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          <div className="sm:col-span-3">
            <label htmlFor="title" className="mb-1 block text-sm font-medium">Meeting title</label>
            <input id="title" className="field" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Weekly Sync (defaults to the file name)" />
          </div>
          <div>
            <label htmlFor="date" className="mb-1 block text-sm font-medium">Meeting date</label>
            <input id="date" type="date" className="field" value={date} onChange={(e) => setDate(e.target.value)} required />
          </div>
          <div>
            <label htmlFor="platform" className="mb-1 block text-sm font-medium">Source</label>
            <select id="platform" className="field" value={platform} onChange={(e) => setPlatform(e.target.value)}>
              <option value="upload">Upload</option>
              <option value="zoom">Zoom</option>
              <option value="teams">Microsoft Teams</option>
              <option value="meet">Google Meet</option>
              <option value="otter">Otter.ai</option>
            </select>
          </div>
        </div>

        {error && <p role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</p>}

        <div className="flex items-center gap-4">
          <button type="submit" className="btn-primary" disabled={busy}>{busy ? "Importing…" : "Import transcript"}</button>
          {busy && <span className="text-sm text-muted">Chunking, embedding and extracting insights. This can take a few seconds.</span>}
        </div>
      </form>
    </div>
  );
}
