# Scout

AI-powered job and internship discovery and auto-apply platform.

## Backend (Phase 1)

### Setup

1. **Python 3.10+** recommended.
2. From project root:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```
3. Create the data directory so SQLite can create the DB file:
   ```bash
   mkdir data
   ```
4. Optional: copy `.env.example` to `backend/.env` (or project root `.env`) and set `SQLITE_PATH` or `DATABASE_URL` if you want a custom DB path. Default is `./data/scout.db` (relative to `backend/` when you run uvicorn from there).

### Run

From the `backend/` directory:

```bash
python -m uvicorn main:app --reload
```

(Using `python -m uvicorn` avoids launcher issues if Python was moved or reinstalled.)

- API base: http://localhost:8000
- Docs: http://localhost:8000/docs

### Endpoints

- **GET /api/listings** — List listings with `limit`, `offset`, `sort` (date | company | score), `min_score`, `max_score`, `remote`, `source`. Each item includes `score` when available.
- **POST /api/listings/scrape** — Trigger a manual scrape. Returns `{ "inserted", "duplicates" }`.
- **POST /api/resume/upload** — Upload resume (PDF/DOCX); parses and stores.
- **GET /api/resume** — Get latest resume data.
- **GET /api/scores/{listing_id}** — Get match score for a listing (computes and caches via Groq).

On startup, the app creates the DB tables, starts a scheduler (scrape every 12 hours), and runs one initial scrape in the background.

---

## Frontend (Phase 3)

### Setup

1. **Node.js 18+** recommended.
2. From project root:
   ```bash
   cd frontend
   npm install
   ```
3. Copy `frontend/.env.local.example` to `frontend/.env.local` and set:
   ```
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```
   (Use the URL where your backend is running.)

### Run

From the `frontend/` directory:

```bash
npm run dev
```

- Dashboard: http://localhost:3000

Ensure the backend is running so the dashboard can load listings.
