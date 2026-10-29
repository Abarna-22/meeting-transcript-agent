# Meeting Transcript Intelligence System

Ask plain-English questions across all your meeting transcripts and get answers with numbered citations
(meeting, date, timestamp). Transcripts also get an automatic summary, action items, decisions and speaker talk-time.

**Stack:** React + Tailwind · FastAPI · MySQL (metadata) · ChromaDB (vectors) · all-MiniLM-L6-v2 embeddings · Groq GPT-OSS 120B

```
Transcript (.txt/.vtt/.srt) -> parser -> chunker (~200 words, 40 overlap) -> embeddings -> ChromaDB
                                    \-> MySQL (meeting, speakers, action items, decisions)
Question -> embed -> top-k chunks (all meetings or one) -> sort oldest first -> LLM -> answer with [n] citations
```

## Run it

### Requirements
- Python 3.11
- Node.js 20+ and npm
- MySQL 8, running locally
- A Groq API key for LLM-generated answers (optional; see "Offline mode")

### Setup
1. From the project root, create the database and user once, using a MySQL admin account:
   ```powershell
   Get-Content .\backend\scripts\setup_mysql.sql | mysql -u root -p
   ```
2. Set up and start the backend in PowerShell:
   ```powershell
   Set-Location .\backend
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   if (-not (Test-Path .env)) { Copy-Item .env.example .env }
   ```
   Edit `backend\.env` and set `GROQ_API_KEY` to your key. The example database URL uses the local `meeting` user created by the SQL script. Tables are created automatically when the backend starts.

   Start the backend:
   ```powershell
   uvicorn app.main:app --reload
   ```
   API docs are available at http://localhost:8000/docs.
3. In a second terminal, start the frontend from the project root:
   ```powershell
   Set-Location .\frontend
   npm install
   npm run dev
   ```
   Open http://localhost:5173.
4. Open the app, create an account with a username, email, and password, and sign in. Passwords must be at least 10 characters.
   Each account can access only its own transcripts. On an existing database, the first account
   created adopts previously unowned meetings.
5. To load the sample meetings, open a third terminal at the project root and sign in when prompted:
   ```powershell
   py -m pip install httpx
   py .\backend\scripts\load_samples.py
   ```

If MySQL is not available, set `DATABASE_URL=sqlite:///./dev.db` in `backend\.env` for development.

## Offline mode
Without `GROQ_API_KEY` the app still runs end to end: answers become the best-matching line from each meeting
(oldest first), and summaries/decisions/action items come from keyword rules. If the MiniLM model cannot be
downloaded, `EMBEDDING_BACKEND=auto` falls back to a hashing embedder. Both fallbacks are labelled in the UI.
Set the Groq key (and let MiniLM download) for real answer quality.

## Tests and evaluation
```powershell
cd backend && pytest -q                       # parser, chunker, ingestion, RAG, auth, filters, API
python scripts/evaluate.py --top-k 3          # hit rate / keyword coverage on data/test_questions.json
```
**Read the numbers carefully.** The six sample meetings only make ~11 chunks, so a large top-k retrieves half
the corpus and "100% hit rate" proves little. For your report, evaluate with `--top-k 3` or lower, on longer
transcripts, with the real MiniLM embeddings and Groq, and add your own questions to `data/test_questions.json`.
Offline hash-embedder results on the sample set: top-1 67%, top-3 87%, top-6 100%.

## API
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/meetings` | upload file or paste text (form fields: `file`/`text`, `title`, `meeting_date`, `platform`) |
| GET | `/api/meetings`, `/api/meetings/{id}` | list / detail (summary, participants, action items, decisions, transcript) |
| DELETE | `/api/meetings/{id}` | remove from MySQL and ChromaDB |
| POST | `/api/query` | `{question, meeting_id?, top_k?, date_from?, date_to?}` -> answer + sources |
| GET | `/api/decisions` | decision log across meetings, oldest first |
| GET/PATCH | `/api/action-items` | filter by `owner`/`status`; mark `open`/`done` |
| GET | `/api/health` | which embedder and LLM mode are active |
| POST | `/api/auth/signup`, `/api/auth/signin` | create an account or start a session |
| GET/POST | `/api/auth/me`, `/api/auth/signout` | inspect the signed-in account or end its session |

## Project layout
```
backend/app/services/  transcript_parser, chunker, embedder, vector_store, llm, rag_engine, ingest
backend/app/routes/    auth, meetings, query
backend/app/models.py  MySQL tables: users, auth_sessions, meetings, participants, action_items, decisions
backend/tests/         pytest suite     backend/scripts/  load_samples.py, evaluate.py
frontend/src/pages/    Ask, Meetings, MeetingDetail, Decisions, Actions, Import
data/                  sample_transcripts/ (6 meetings with a budget that changes 5 -> 7 lakhs), test_questions.json
```

## Known limits
- Tables are created on startup (`create_all`); there are no Alembic migrations yet.
- Accounts use email/password and expiring bearer sessions. Email verification, password reset, and sign-in rate limiting are not implemented; add these and use HTTPS before public deployment.
- Ingestion runs inside the upload request. Very long transcripts take longer; a background queue is the next step.
- Zoom/Otter API import is not built (file upload and paste only).
- Speaker talk-time is exact only when the transcript has timestamps; otherwise it is estimated from word counts.
