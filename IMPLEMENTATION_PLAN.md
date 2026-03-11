    # Scout — Phase-Wise Implementation Plan

Based on the PRD (`job-autopilot-prd.md`). Project codename in PRD: Job Autopilot; product name for this repo: **Scout**.

---

## Phase 1 — Core Scraping + Database ✅ COMPLETE

### 1. GOAL
Establish the backend foundation: SQLite schema, Remotive + We Work Remotely scrapers, deduplication by job URL, and APScheduler running a daily scrape so listings are stored and ready for the dashboard.

### 2. FILES TO CREATE OR MODIFY

| Action | Path |
|--------|------|
| Create | `backend/main.py` — FastAPI app entry, CORS, router includes |
| Create | `backend/db/database.py` — SQLite connection, session factory |
| Create | `backend/db/models.py` — SQLAlchemy models: `listings` (and any supporting tables) |
| Create | `backend/scrapers/__init__.py` |
| Create | `backend/scrapers/remotive.py` — Remotive REST API fetcher |
| Create | `backend/scrapers/weworkremotely.py` — We Work Remotely RSS fetcher |
| Create | `backend/scrapers/base.py` — Shared types/helpers (e.g. `ListingRow`) |
| Create | `backend/scheduler.py` — APScheduler, register scrape job, run on interval |
| Create | `backend/config.py` — Settings (e.g. from env), DB path |
| Create | `backend/requirements.txt` — FastAPI, uvicorn, SQLAlchemy, aiohttp, feedparser, APScheduler, etc. |
| Create | `.env.example` — Document `DATABASE_URL` (or `SQLITE_PATH`), no secrets yet |
| Create | `README.md` — How to run backend, install deps, env vars |

### 3. TASKS

1. Define SQLAlchemy model for `listings`: `id`, `title`, `company`, `location`, `remote` (bool), `description`, `apply_url`, `source`, `date_posted`, `date_fetched`, `created_at`. Use `apply_url` (or normalized URL) as dedupe key.
2. Implement `database.py`: create engine/session for SQLite, init tables on startup.
3. Implement `config.py`: load `DATABASE_URL` or `SQLITE_PATH` from env; default SQLite path e.g. `./data/scout.db`.
4. Implement Remotive scraper: GET Remotive API, map response to listing rows, return list of dicts/models.
5. Implement We Work Remotely scraper: parse RSS feed, map items to same listing shape, return list.
6. Add deduplication: before insert, check if `apply_url` (or canonical URL) exists; only insert new listings. Log counts: new vs duplicate.
7. Wire scrapers in `scheduler.py`: run both scrapers, merge results, dedupe and insert via DB layer. Catch per-source errors so one failure doesn’t stop others; log errors.
8. Expose `POST /api/listings/scrape` in FastAPI to trigger a manual run (same logic as scheduler).
9. Expose `GET /api/listings`: return all listings (no filters yet), with optional `limit`/`offset` for basic pagination.
10. On app startup, run initial scrape once (or on first request) and start APScheduler (e.g. every 12h for Remotive/WFR per PRD).

### 4. DEPENDENCIES

```bash
# Backend (from project root: backend/)
pip install fastapi uvicorn[standard] sqlalchemy aiohttp feedparser apscheduler python-dotenv
```

(Add exact versions in `backend/requirements.txt`.)

### 5. ENVIRONMENT VARIABLES

| Key | Where to get it | Required this phase |
|-----|-----------------|----------------------|
| `DATABASE_URL` or `SQLITE_PATH` | Optional; default `./data/scout.db` | No (default works) |

None of the scrapers in this phase require API keys (Remotive public API, WFR public RSS).

### 6. USER ACTION REQUIRED

- Create `backend/data/` (or ensure working directory allows creation of `./data/scout.db`).
- Run backend: `cd backend && uvicorn main:app --reload`.
- Call `POST /api/listings/scrape`, then `GET /api/listings` and confirm listings appear (Remotive + WFR).
- Optionally trigger scheduler and wait one cycle or inspect logs to confirm scheduled run.

### 7. DONE CRITERIA

- Remotive and We Work Remotely listings are fetched and stored in SQLite.
- Duplicate listings (same apply URL) are not inserted twice.
- `GET /api/listings` returns stored listings; `POST /api/listings/scrape` triggers a run.
- Scheduler runs every 12 hours (or configured interval) without crashing; one failing source doesn’t break the others.
- No API keys required for Phase 1.

---

## Phase 2 — Resume Parsing + AI Match Scoring ✅ COMPLETE

### 1. GOAL
Allow resume upload (PDF/DOCX), parse and store structured resume data, and score each listing against that resume using Groq with results cached in the DB.

### 2. FILES TO CREATE OR MODIFY

| Action | Path |
|--------|------|
| Create | `backend/db/models.py` — Add `resume` and `scores` tables (or extend existing) |
| Create | `backend/resume/parser.py` — PDF (pdfplumber) + DOCX (python-docx) extraction, return structured dict |
| Create | `backend/ai/__init__.py` |
| Create | `backend/ai/matcher.py` — Call Groq API with resume summary + job description, return score JSON |
| Create | `backend/main.py` — Add routes: `POST /api/resume/upload`, `GET /api/resume`, `GET /api/scores/{listing_id}`, optional background score job |
| Modify | `backend/requirements.txt` — Add pdfplumber, python-docx, groq |
| Modify | `.env.example` — Add `GROQ_API_KEY` |

### 3. TASKS

1. Define `resume` table: `id`, `raw_text`, `skills` (JSON or separate table), `experience`, `education`, `preferred_roles`, `updated_at`. Store parsed output.
2. Define `scores` table: `id`, `listing_id`, `overall_score`, `skills_score`, `experience_score`, `role_score`, `reasoning`, `scored_at`.
3. Implement resume parser: extract text from PDF/DOCX, then parse into skills, experience, education (simple heuristics or regex); return dict matching resume schema.
4. Implement `POST /api/resume/upload`: accept file upload, run parser, save to `resume` table.
5. Implement `GET /api/resume`: return latest parsed resume data.
6. Implement `ai/matcher.py`: build prompt with resume summary + job description, call Groq (e.g. llama3-70b), parse JSON response (`overall`, `skills_match`, `experience_match`, `role_match`, `reasoning`); cache in `scores` by `listing_id`; skip if score already exists for that listing/resume version if desired.
7. Implement `GET /api/scores/{listing_id}`: return score from DB or compute on-demand and cache.
8. Optional: after scrape or on new listing, enqueue score calculation (in-process or background) so listings get scores over time.

### 4. DEPENDENCIES

```bash
pip install pdfplumber python-docx groq
```

### 5. ENVIRONMENT VARIABLES

| Key | Where to get it | Required this phase |
|-----|-----------------|----------------------|
| `GROQ_API_KEY` | https://console.groq.com — create API key | Yes (for scoring) |

### 6. USER ACTION REQUIRED

- Get Groq API key from console.groq.com; add to `.env` as `GROQ_API_KEY`.
- Upload a PDF or DOCX resume via `POST /api/resume/upload`.
- Call `GET /api/scores/{listing_id}` for a known listing_id and confirm JSON with `overall`, `reasoning`, etc.

### 7. DONE CRITERIA

- Resume upload and parsing work; `GET /api/resume` returns structured data.
- For a given listing, `GET /api/scores/{listing_id}` returns a cached or newly computed score (0–100) with reasoning.
- Scores are stored in DB and not recomputed unnecessarily for the same listing/resume.

---

## Phase 3 — Dashboard MVP (Next.js) ✅ COMPLETE

### 1. GOAL
Ship a Next.js 14 (App Router) dashboard that shows all listings with filters, sorting, score badges, and pagination, consuming the FastAPI backend.

### 2. FILES TO CREATE OR MODIFY

| Action | Path |
|--------|------|
| Create | `frontend/package.json` — Next.js 14, React, Tailwind, shadcn/ui deps |
| Create | `frontend/next.config.js` |
| Create | `frontend/tailwind.config.js` |
| Create | `frontend/tsconfig.json` |
| Create | `frontend/app/layout.tsx` — Root layout |
| Create | `frontend/app/page.tsx` — Dashboard: list of listings |
| Create | `frontend/app/globals.css` — Tailwind imports |
| Create | `frontend/components/ListingCard.tsx` — Title, company, location, remote badge, score badge, date, source, expand description |
| Create | `frontend/components/FilterBar.tsx` — Score range, location, remote, source, sort (score, date, company) |
| Create | `frontend/components/ScoreBadge.tsx` — 0–100 coloured badge (e.g. green/yellow/red) |
| Create | `frontend/lib/api.ts` — Client helpers: fetch listings (with query params), base URL from env |
| Create | `frontend/.env.local.example` — `NEXT_PUBLIC_API_URL=http://localhost:8000` |

### 3. TASKS

1. Bootstrap Next.js 14 app with TypeScript and Tailwind; add shadcn/ui (or manual components with Tailwind).
2. Implement `lib/api.ts`: `getListings({ page, limit, sort, minScore, maxScore, remote, source })` calling FastAPI `GET /api/listings` and optional `GET /api/scores/{id}` if not embedded in listing response.
3. Ensure backend `GET /api/listings` supports query params: `limit`, `offset`, `sort`, `min_score`, `max_score`, `remote`, `source` and returns total count.
4. Build `ListingCard`: show title, company, location, remote badge, score (from API or embedded), date posted, source; expand/collapse for description.
5. Build `ScoreBadge`: numeric score with colour by range (e.g. 70–100 green, 40–69 yellow, 0–39 red).
6. Build `FilterBar`: inputs for score range, location, remote (yes/no), source dropdown, sort (score desc, date, company); on change, refetch listings.
7. Implement pagination: 25 per page (configurable 25/50/100), show total count and next/prev.
8. Dashboard page: load listings on mount and when filters change; show loading and empty states.

### 4. DEPENDENCIES

```bash
cd frontend && npm install next@14 react react-dom
npm install -D tailwindcss postcss autoprefixer typescript @types/node @types/react
# If using shadcn: npx shadcn-ui@latest init
```

### 5. ENVIRONMENT VARIABLES

| Key | Where to get it | Required this phase |
|-----|-----------------|----------------------|
| `NEXT_PUBLIC_API_URL` | Your FastAPI base URL, e.g. `http://localhost:8000` | Yes |

### 6. USER ACTION REQUIRED

- Set `NEXT_PUBLIC_API_URL` in `frontend/.env.local`.
- Run backend and frontend; open dashboard, confirm listings load, filters and sort work, score badges show, pagination works.

### 7. DONE CRITERIA

- Dashboard displays all listings from the API with filters (score range, location, remote, source), sort (score, date, company), and pagination (25/50/100).
- Score badge shows per listing (colour-coded); description expand/collapse works.
- No placeholders or TODOs; ready for Phase 4.

---

## Phase 4 — Cover Letter Engine ✅ COMPLETE

### 1. GOAL
Generate a unique cover letter per listing using Gemini, store in DB, and provide an editor in the dashboard with regenerate, version history (up to 3), and export (copy, PDF, DOCX).

### 2. FILES TO CREATE OR MODIFY

| Action | Path |
|--------|------|
| Create | `backend/ai/cover_letter.py` — Gemini client, prompt (resume + job + company), return 3–4 paragraph letter |
| Create | `backend/db/models.py` — Add `cover_letters` table: listing_id, content, version, tone, generated_at, edited_by_user |
| Modify | `backend/main.py` — `POST /api/cover-letter/generate`, `PUT /api/cover-letter/{id}`, `GET /api/listings/{id}` (include cover letter) |
| Create | `frontend/components/CoverLetterEditor.tsx` — Rich text (TipTap or Quill), Regenerate, version history (up to 3), Copy / Download PDF / DOCX |
| Modify | `frontend/components/ListingCard.tsx` — Buttons: View Cover Letter, Edit Cover Letter, Apply Now (placeholder), Save for Later, Dismiss |
| Modify | `frontend/app/page.tsx` or modal/drawer — Show CoverLetterEditor for selected listing |
| Modify | `backend/requirements.txt` — Add google-generativeai (or Gemini SDK) |
| Modify | `.env.example` — Add `GEMINI_API_KEY` |

### 3. TASKS

1. Add `cover_letters` table: `id`, `listing_id`, `content`, `version` (1–3), `tone`, `generated_at`, `edited_by_user` (bool).
2. Implement `ai/cover_letter.py`: input resume summary, job title, company, full job description; call Gemini 1.5 Flash; return 3–4 paragraph letter (max 400 words); support tone option (Professional, Conversational, Technical, Enthusiastic).
3. Implement `POST /api/cover-letter/generate`: body `listing_id`, optional `tone`; create or rotate version (keep max 3); store in DB.
4. Implement `PUT /api/cover-letter/{id}`: update `content`, set `edited_by_user=true`.
5. Implement `GET /api/listings/{id}`: include latest cover letter for listing.
6. Frontend: CoverLetterEditor with rich text editor; load letter from API; Regenerate button calls generate API and appends as new version; show version dropdown (up to 3).
7. Export: Copy to clipboard; Download as PDF (e.g. browser print or lib); Download as DOCX (e.g. docx lib or simple HTML→DOCX).
8. ListingCard: “View Cover Letter” opens editor in modal/drawer; “Edit Cover Letter” focuses editor; Apply Now/Save/Dismiss can be stubs or update application status (Phase 6).

### 4. DEPENDENCIES

```bash
# Backend
pip install google-generativeai

# Frontend (if not already)
npm install @tiptap/react @tiptap/starter-kit
# Or quill + react-quill; for DOCX: docx or file-saver + blob
```

### 5. ENVIRONMENT VARIABLES

| Key | Where to get it | Required this phase |
|-----|-----------------|----------------------|
| `GEMINI_API_KEY` | https://aistudio.google.com/app/apikey — Create API key | Yes |

### 6. USER ACTION REQUIRED

- Get Gemini API key; add `GEMINI_API_KEY` to backend `.env`.
- In dashboard, open a listing → View Cover Letter → Generate; confirm letter appears; test Regenerate and version switch; test Copy and export (PDF/DOCX).

### 7. DONE CRITERIA

- Cover letter is generated for a listing via Gemini and stored; versioning (max 3) works.
- Dashboard editor loads and saves edited content; Regenerate creates new version.
- Export: copy, PDF, and DOCX work; no placeholders.

---

## Phase 5 — Auto-Apply Engine ✅ COMPLETE

### 1. GOAL
Support one-click “Apply Now” with auto-apply for Greenhouse and Lever APIs, and Playwright for simple HTML forms and Remotive-style flows; human-in-the-loop confirmation by default; manual fallback (open URL + copy cover letter to clipboard).

### 2. FILES TO CREATE OR MODIFY

| Action | Path |
|--------|------|
| Create | `backend/applier/__init__.py` |
| Create | `backend/applier/greenhouse_apply.py` — POST to Greenhouse API with resume + cover letter |
| Create | `backend/applier/lever_apply.py` — POST to Lever API |
| Create | `backend/applier/playwright_apply.py` — Detect form, fill name/email/resume/cover letter, submit; optional headless flag |
| Create | `backend/applier/dispatcher.py` — Detect apply flow type from listing (URL/source), call appropriate applier; return success/fail/manual_required |
| Modify | `backend/main.py` — `POST /api/apply/{listing_id}` with optional `confirm=true` (or body); optional Yolo Mode from user prefs |
| Modify | `backend/db/models.py` — Add `applications` table: listing_id, status, applied_at, apply_method, notes |
| Modify | `frontend/components/ListingCard.tsx` — Apply Now calls API; show confirmation modal unless Yolo; on success/fail show message; “Open in browser + copy letter” for manual fallback |
| Modify | `backend/requirements.txt` — Add playwright; run `playwright install chromium` |

### 3. TASKS

1. Add `applications` table: `id`, `listing_id`, `status` (e.g. New, Applied, Interview, Offer, Rejected), `applied_at`, `apply_method` (greenhouse/lever/playwright/manual), `notes`.
2. Implement Greenhouse applier: parse job URL for job id if needed; POST to `/jobs/{id}/applications` with resume + cover letter; handle success/error.
3. Implement Lever applier: POST to Lever postings apply endpoint; same idea.
4. Implement Playwright applier: launch browser, navigate to apply_url, fill common field selectors (name, email, resume file, cover letter text); submit; return success/failure; add human-like delay and optional headless=false.
5. Implement dispatcher: if apply_url is Greenhouse/Lever, use API; else try Playwright; on failure or unsupported, return manual_required and apply_url + cover letter text.
6. Implement `POST /api/apply/{listing_id}`: require confirmation (query or body) unless Yolo Mode; get listing + cover letter + resume path; call dispatcher; insert/update `applications` row; return result.
7. Frontend: Apply Now → confirmation modal (“Submit application?”) → call API; on success show “Applied”; on manual_required open URL in new tab and copy cover letter to clipboard (and show toast).
8. Document in README: Playwright install (`playwright install chromium`), and that LinkedIn auto-apply is out of scope (display only).

### 4. DEPENDENCIES

```bash
pip install playwright
playwright install chromium
```

### 5. ENVIRONMENT VARIABLES

| Key | Where to get it | Required this phase |
|-----|----------------|---------------------|
| (Optional) `PLAYWRIGHT_HEADLESS` | `true`/`false` | No (default true) |
| (Optional) `RESUME_FILE_PATH` | Path to default resume file for uploads | No |

No API keys for Greenhouse/Lever from the user’s side; those are public job application endpoints. If backend uses internal API keys for any provider, document in .env.example.

### 6. USER ACTION REQUIRED

- Run `playwright install chromium` once.
- Test Apply with a listing that uses Greenhouse or Lever; test one with a simple HTML form; test manual fallback (e.g. LinkedIn or HN) and confirm URL opens and copy works.

### 7. DONE CRITERIA

- Apply Now with confirmation submits via Greenhouse or Lever API when applicable; otherwise via Playwright when possible.
- Unsupported or failed flows fall back to “open in browser + copy cover letter” and show clear message.
- Application is recorded in `applications` table with status and method; dashboard can show “Applied” for that listing.

**Phase 5 — COMPLETE.** Apply endpoint and ApplyConfirmBody in `main.py`; Application model and applier (Playwright + dispatcher) in place. Frontend: Apply Now → confirmation modal → API; manual fallback opens URL and copies cover letter. `playwright` in requirements; run `playwright install chromium` once.

---

## Phase 6 — Application Tracker ✅ COMPLETE

### 1. GOAL
Kanban board and table view for application pipeline (Saved → Applied → Phone Screen → Interview → Offer / Rejected), with notes, follow-up date, and CSV export.

### 2. FILES TO CREATE OR MODIFY

| Action | Path |
|--------|------|
| Create | `frontend/app/tracker/page.tsx` — Tracker view (tabs or sections: Kanban + Table) |
| Create | `frontend/components/KanbanBoard.tsx` — Columns by status, drag-and-drop cards (listing title, company, applied date) |
| Create | `frontend/components/ApplicationsTable.tsx` — Sortable columns: listing, company, status, applied date, notes, follow-up |
| Modify | `backend/main.py` — `GET /api/applications`, `PUT /api/applications/{id}` (status, notes, follow_up_date) |
| Create | `frontend/components/ApplicationCard.tsx` — Card in Kanban with optional notes editor and follow-up date |
| Modify | `backend/main.py` — `GET /api/applications/export?format=csv` (or similar) |

### 3. TASKS

1. Backend: `GET /api/applications` — return all applications with listing summary (title, company, apply_url), status, applied_at, apply_method, notes, follow_up_date; support sort/filter by status.
2. Backend: `PUT /api/applications/{id}` — update status, notes, follow_up_date.
3. Frontend: Kanban board with columns: Saved | Applied | Phone Screen | Interview | Offer | Rejected; drag-and-drop to update status (call PUT on drop).
4. Frontend: Table view with same data; sortable columns; inline edit for notes and follow-up date.
5. Add “Save for Later” from listing card: creates application with status Saved (if not already applied).
6. Export: endpoint or frontend-generated CSV with columns: title, company, status, applied_at, notes, follow_up_date; trigger download.

### 4. DEPENDENCIES

```bash
# Frontend (if not already)
npm install @dnd-kit/core @dnd-kit/sortable  # or react-beautiful-dnd / similar for Kanban
```

### 5. ENVIRONMENT VARIABLES

None new.

### 6. USER ACTION REQUIRED

- Move a few applications through Kanban columns; add notes and follow-up dates; export CSV and open in Excel/Sheets.

### 7. DONE CRITERIA

- Kanban board shows all applications by status; drag-and-drop updates status via API.
- Table view shows same data with sort and inline edit for notes/follow-up.
- CSV export downloads with all application fields; “Save for Later” creates an application in Saved.

---

## Phase 7 — Polish + Deploy

### 1. GOAL
Dockerize app, add README with setup and env vars, optional CI (GitHub Actions), and deploy frontend to Vercel and backend to Railway/Render.

### 2. FILES TO CREATE OR MODIFY

| Action | Path |
|--------|------|
| Create | `backend/Dockerfile` — Python 3.11+, install deps + Playwright, run uvicorn |
| Create | `frontend/Dockerfile` — Optional; Vercel prefers git-based deploy |
| Create | `docker-compose.yml` — Backend service only (SQLite volume); optional Redis for future Celery |
| Modify | `README.md` — Project overview, setup (backend + frontend), all env vars, how to run scrape, scheduler, apply, tracker |
| Create | `.github/workflows/ci.yml` — Lint backend (ruff/flake8) and frontend (next lint); optional pytest for backend |
| Modify | `.env.example` — Full list of keys with comments |
| Create | `backend/scripts/run_scheduler.py` or document running with scheduler in same process |

### 3. TASKS

1. Backend Dockerfile: FROM python:3.11-slim; install deps + Playwright chromium; COPY app; CMD uvicorn.
2. docker-compose: backend service, volume for SQLite data; env_file .env.
3. README: clone, backend env (GROQ, GEMINI, DATABASE_URL), frontend env (NEXT_PUBLIC_API_URL), run backend + frontend, run migrations if any, optional Docker.
4. GitHub Actions: on push, run backend lint and optional tests; run `next lint` for frontend.
5. Document deploy: Vercel for frontend (connect repo, set NEXT_PUBLIC_API_URL to production API); Railway/Render for backend (set env vars, use Dockerfile or buildpack).
6. Ensure production backend uses a persistent DB (e.g. Supabase Postgres or Railway volume for SQLite) and document in README.

### 4. DEPENDENCIES

Docker, Docker Compose; optional: ruff, pytest. No new pip/npm unless adding CI deps.

### 5. ENVIRONMENT VARIABLES

Document all in README and .env.example: `DATABASE_URL`, `GROQ_API_KEY`, `GEMINI_API_KEY`, `NEXT_PUBLIC_API_URL`, optional `PLAYWRIGHT_HEADLESS`, `RESUME_FILE_PATH`.

### 6. USER ACTION REQUIRED

- Create Vercel and Railway (or Render) accounts; connect repo; set production env vars; deploy and smoke-test (listings load, apply works, tracker works).

### 7. DONE CRITERIA

- Backend runs in Docker; docker-compose up brings backend up with SQLite.
- README allows a new developer to run Scout locally and deploy to Vercel + Railway.
- CI runs on push and passes; production URLs work for dashboard and API.

---

## Summary Table

| Phase | Goal | New env vars |
|-------|------|--------------|
| 1 | Scraping + DB (Remotive, WFR, scheduler) | — |
| 2 | Resume parsing + Groq match scoring | `GROQ_API_KEY` |
| 3 | Next.js dashboard (listings, filters, scores, pagination) | `NEXT_PUBLIC_API_URL` |
| 4 | Cover letter (Gemini, editor, versions, export) | `GEMINI_API_KEY` |
| 5 | Auto-apply (Greenhouse, Lever, Playwright, fallback) | — |
| 6 | Application tracker (Kanban, table, CSV export) | — |
| 7 | Docker, README, CI, deploy (Vercel + Railway) | (document all) |

---

*Once you approve this plan, implementation will proceed one phase at a time. Say "looks good, start implementation" to begin with Phase 1.*
