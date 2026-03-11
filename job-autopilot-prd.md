# Job Autopilot — Product Requirements Document

**Version:** v1.0 | **Status:** Draft | **Last Updated:** February 2026
**Document Type:** Product Requirements Document | **Classification:** Confidential

---

## Table of Contents

1. [Product Overview](#1-product-overview)
2. [Goals & Success Metrics](#2-goals--success-metrics)
3. [User Personas](#3-user-personas)
4. [Scope & Feasibility](#4-scope--feasibility)
5. [Feature Requirements](#5-feature-requirements)
6. [Technical Architecture](#6-technical-architecture)
7. [Project Structure](#7-project-structure)
8. [Development Milestones](#8-development-milestones)
9. [Non-Functional Requirements](#9-non-functional-requirements)
10. [Risks & Mitigations](#10-risks--mitigations)
11. [Future Enhancements](#11-future-enhancements-v2)
12. [Glossary](#12-glossary)

---

## 1. Product Overview

Job Autopilot is a full-stack AI-powered platform that automates the end-to-end job and internship search process. It continuously scrapes listings from multiple sources, scores them against the user's resume and preferences, displays **every listing** in a sortable dashboard, generates a tailored cover letter for each role, and — where technically feasible — auto-fills and submits applications on behalf of the user.

> **Core Philosophy:** Automate the finding, filtering, and writing. Keep the human in the loop for final submission. This design is both ethical and practically superior — mass-blind applying tanks response rates. Job Autopilot surfaces everything so users can make informed decisions, then acts fast on their behalf.

### 1.1 Problem Statement

Job searching is time-consuming and repetitive. Candidates must manually visit dozens of job boards, copy-paste their resume context into each application, write fresh cover letters for every role, and track their pipeline in spreadsheets. This process takes hours per week and is prone to missed opportunities and inconsistent quality.

### 1.2 Solution

A single platform that:

- Fetches **ALL** job and internship listings from multiple sources on a schedule
- Displays every listing in a filterable, sortable dashboard — not just top matches
- Scores each listing for match quality to help users prioritise
- Generates a unique, high-quality cover letter for every role using AI
- Auto-applies to supported platforms via browser automation
- Tracks the full application pipeline from discovery to offer

---

## 2. Goals & Success Metrics

### 2.1 Primary Goals

- Reduce job search time by 80% compared to manual searching
- Surface 100% of available listings (no silent filtering at fetch stage)
- Generate cover letters indistinguishable in quality from manually written ones
- Achieve >70% auto-apply success rate on supported platforms
- Give users full visibility and control over every application submitted

### 2.2 Success Metrics

| Metric | Target | Measurement Method |
|---|---|---|
| Listings fetched per run | > 200 across all sources | DB row count post-scrape |
| AI match score accuracy | > 80% user agreement | User feedback thumbs up/down |
| Cover letter acceptance rate | > 85% used without edits | Edit tracking in dashboard |
| Auto-apply success rate | > 70% on supported platforms | Form submission confirmation |
| Dashboard load time | < 2 seconds for 500 listings | Lighthouse / API timing |
| Daily scrape reliability | > 99% uptime | Scheduler health checks |

---

## 3. User Personas

| Persona | Description | Primary Need |
|---|---|---|
| Final Year CS Student | Applying to 50+ roles simultaneously, limited time | Maximum coverage + AI cover letters |
| Recent Graduate | 2–6 months post-graduation, targeting specific stacks | Precision filtering + auto-apply |
| Career Switcher | Pivoting roles, resume mismatch anxiety | Match scoring + cover letter tailoring |
| Internship Hunter | Targeting summer/semester internships by deadline | Deadline tracking + bulk apply |

---

## 4. Scope & Feasibility

### 4.1 What Is In Scope

- Job scraping from: Remotive, We Work Remotely, Wellfound, GitHub Jobs, HN Who's Hiring, Indeed (public), LinkedIn (public listings only)
- Full listing display in dashboard — all fetched results, not filtered
- AI-powered match scoring (0–100) shown per listing
- Filters: score range, location, remote/hybrid, experience level, date posted, company, tech stack
- AI cover letter generation per listing using Groq / Gemini free APIs
- Auto-apply via Playwright on: simple HTML forms, Greenhouse API, Lever API, Remotive apply flows
- Application status tracker: New → Applied → Interview → Offer / Rejected
- Resume upload and parsing
- Daily scheduled scrape with deduplication

### 4.2 What Is Out of Scope (v1)

- LinkedIn auto-apply (ToS violation, account ban risk — flagged explicitly)
- Workday / iCIMS / SAP SuccessFactors (too complex, highly variable forms)
- Multi-user / team accounts
- Mobile app
- Email follow-up automation

### 4.3 Platform Feasibility Matrix

| Platform | Scraping | Auto-Apply | Notes |
|---|---|---|---|
| Remotive API | ✅ Yes | ✅ Full | Free JSON API, direct apply links |
| We Work Remotely | ✅ Yes | ⚠️ Partial | RSS feed, redirects to company sites |
| Wellfound (AngelList) | ✅ Yes | ⚠️ Partial | Public listings, auth needed for apply |
| HN Who's Hiring | ✅ Yes | ❌ No | Text posts, email-based applications |
| GitHub Jobs (via search) | ✅ Yes | ⚠️ Partial | Scrape public listings |
| Greenhouse (API) | ✅ Yes | ✅ Full | Official API available |
| Lever (API) | ✅ Yes | ✅ Full | Official API available |
| Indeed (public) | ✅ Yes | ⚠️ Partial | Some apply flows automatable |
| LinkedIn (public) | ✅ Yes | ❌ Blocked | Bot detection, ToS risk — display only |
| Workday | ⚠️ Limited | ❌ Blocked | Heavy anti-bot measures |

---

## 5. Feature Requirements

### 5.1 Job Scraping Engine

#### 5.1.1 Requirements

- Fetch listings from all configured sources on a 24-hour schedule (APScheduler)
- Store raw listing data: title, company, location, remote flag, description, apply URL, source, date posted, date fetched
- Deduplicate by job URL — never show the same listing twice
- Run initial fetch on first launch, then on schedule
- Log scrape results: listings found, new vs duplicate, errors per source
- Graceful failure handling — if one source fails, continue others

#### 5.1.2 Data Sources & Methods

| Source | Method | Frequency | Expected Volume |
|---|---|---|---|
| Remotive | REST API (JSON) | Every 12h | ~50–100 listings |
| We Work Remotely | RSS Feed | Every 12h | ~30–60 listings |
| Wellfound | Playwright scraper | Every 24h | ~40–80 listings |
| HN Who's Hiring | HN API (monthly thread) | Monthly | ~200–500 listings |
| Greenhouse jobs | Company-specific API | Every 24h | Variable |
| Lever jobs | Company-specific API | Every 24h | Variable |
| Indeed | Playwright scraper | Every 24h | ~100–200 listings |
| LinkedIn | Playwright scraper | Every 24h | ~100–300 listings (display only) |

---

### 5.2 Dashboard — All Listings View

> **Design Decision: Show ALL listings regardless of score.** Match score is a guide, not a gatekeeper. Some of the best opportunities have low match scores because the job description uses different terminology. The user sees everything and uses score as a prioritisation signal, not a filter gate. Sorting by score descending is the default view.

#### 5.2.1 Listing Card

- Job title, company name, location / remote badge
- AI match score displayed as a coloured badge (0–100, green/yellow/red)
- Date posted + source platform icon
- Tech stack tags parsed from description
- Expand/collapse job description inline
- Buttons: View Cover Letter, Edit Cover Letter, Apply Now, Save for Later, Dismiss

#### 5.2.2 Filtering & Sorting

- Filter by: match score range, location, remote/hybrid/on-site, experience level, source, tech stack, date posted, applied / not applied
- Sort by: match score (default), date posted, company name, application deadline
- Search bar: full-text search across title, company, and description
- Saved filter presets (e.g. "Remote Python roles > 70%")
- Show count of total listings + filtered results

#### 5.2.3 Pagination

- Show 25 listings per page by default
- Configurable: 25 / 50 / 100 per page
- Total listing count always visible

---

### 5.3 AI Match Scoring

#### 5.3.1 How Scoring Works

- Parse user resume (PDF/DOCX) to extract: skills, experience years, past roles, education, preferred role types
- For each job listing, send resume summary + job description to Groq/Gemini API
- Prompt AI to return a JSON score object:
  ```json
  {
    "overall": 82,
    "skills_match": 90,
    "experience_match": 75,
    "role_match": 85,
    "reasoning": "Strong Python and FastAPI skills match. Missing Kubernetes experience mentioned in JD."
  }
  ```
- Cache scores in DB — do not re-score unless listing or resume changes
- Display score breakdown on hover/expand

---

### 5.4 AI Cover Letter Generator

#### 5.4.1 Generation Logic

- Triggered: automatically on new listing discovery (background job), or manually by user
- Input context sent to AI: user resume summary, job title, company name, full job description, company info (if fetchable), user tone preference
- Output: a 3–4 paragraph cover letter, no filler phrases, role-specific
- Stored per listing in DB — one draft per listing, editable

#### 5.4.2 Cover Letter Structure

- **Paragraph 1:** Specific hook mentioning the role and company by name
- **Paragraph 2:** Most relevant experience mapped to job requirements
- **Paragraph 3:** Why this company specifically (pulled from job description context)
- **Paragraph 4:** Call to action + contact
- Tone options: Professional, Conversational, Technical, Enthusiastic
- Max length: 400 words

#### 5.4.3 Editing

- Rich text editor in dashboard (TipTap or Quill)
- Regenerate button — create a new version without overwriting current
- Version history: keep up to 3 versions per listing
- Export: copy to clipboard, download as PDF, download as DOCX

---

### 5.5 Auto-Apply Engine

#### 5.5.1 Supported Apply Flows

| Flow Type | How It Works | Success Rate Estimate |
|---|---|---|
| Greenhouse API | POST to `/jobs/{id}/applications` with resume + cover letter | ~95% |
| Lever API | POST to `/postings/{id}/apply` | ~95% |
| Simple HTML Forms | Playwright fills name/email/resume/cover letter fields | ~70% |
| Remotive direct apply | Playwright follows apply link and fills form | ~65% |
| Manual fallback | Open job URL in browser, cover letter pre-copied to clipboard | 100% (user submits) |

#### 5.5.2 Apply Flow

1. User reviews listing + cover letter in dashboard
2. Clicks **Apply Now** — system detects apply flow type
3. If supported: auto-fill and submit, show confirmation
4. If unsupported: open browser tab, copy cover letter to clipboard, show guidance
5. Log result: Applied / Failed / Manual Required
6. On failure: show error, offer retry or manual fallback

> **Safety Note — Human-in-the-Loop Confirmation:** By default, all auto-apply actions require a single confirmation click from the user before submission. A **Yolo Mode** toggle (off by default) allows fully automated submission for users who explicitly opt in. This design prevents accidental mass applications and protects the user's professional reputation.

---

### 5.6 Application Tracker

- Status pipeline: Saved → Applied → Phone Screen → Interview → Offer → Rejected
- Drag-and-drop Kanban board view
- Table view with sortable columns
- Notes field per application (interview prep, contacts, salary info)
- Applied date, last updated date
- Reminders: set follow-up date, get in-app notification
- Export pipeline to CSV

---

### 5.7 Resume & Profile Setup

- Upload resume as PDF or DOCX
- System parses and extracts: skills, experience, education, preferred roles, preferred locations, remote preference
- User can review and edit parsed data in a structured form
- Profile preferences: target roles, min/max experience level, must-have skills, deal-breaker keywords
- These preferences influence match scoring and are always editable

---

## 6. Technical Architecture

### 6.1 Technology Stack

| Layer | Technology | Cost | Rationale |
|---|---|---|---|
| Frontend | Next.js 14 (App Router) | Free | SSR, API routes, great DX |
| UI Components | Tailwind CSS + shadcn/ui | Free | Fast, consistent styling |
| Backend / API | FastAPI (Python) | Free | Async, fast, great for AI integrations |
| Scraping / Automation | Playwright (Python) | Free | Best browser automation library |
| AI — Matching | Groq API (llama3-70b) | Free tier | Fast inference, generous free quota |
| AI — Cover Letters | Google Gemini 1.5 Flash | Free tier | Excellent writing quality, free |
| Resume Parsing | pdfplumber + python-docx | Free | No external API needed |
| Database | SQLite (dev) / Supabase (prod) | Free | Zero cost, easy migration |
| Task Scheduling | APScheduler (Python) | Free | Lightweight, in-process scheduling |
| Job Queue (optional) | Celery + Redis (Upstash free) | Free tier | If scaling scrapes is needed |
| Hosting — Frontend | Vercel | Free tier | Best Next.js hosting |
| Hosting — Backend | Railway / Render | Free tier | Free persistent backend |
| Version Control | GitHub | Free | CI/CD via GitHub Actions |

### 6.2 System Architecture — High-Level Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        SCHEDULER (APScheduler)                  │
│                    Runs every 12–24 hours                       │
└──────────────────────────┬──────────────────────────────────────┘
                           │
              ┌────────────▼────────────┐
              │     SCRAPER MODULES     │
              │  Remotive / WFR /       │
              │  Wellfound / Indeed /   │
              │  LinkedIn / HN / etc.   │
              └────────────┬────────────┘
                           │ New listings (deduplicated)
              ┌────────────▼────────────┐
              │       DATABASE          │
              │  SQLite / Supabase      │
              │  listings, scores,      │
              │  cover_letters,         │
              │  applications, resume   │
              └─────┬──────────┬────────┘
                    │          │
       ┌────────────▼──┐   ┌───▼────────────────┐
       │  AI MATCHER   │   │  COVER LETTER GEN  │
       │  Groq API     │   │  Gemini API        │
       │  Score 0–100  │   │  Per listing       │
       └────────────┬──┘   └───┬────────────────┘
                    │          │
              ┌─────▼──────────▼────────┐
              │     FASTAPI BACKEND     │
              │     REST API Layer      │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────┐
              │    NEXT.JS DASHBOARD    │
              │  All Listings View      │
              │  Cover Letter Editor    │
              │  Application Tracker    │
              └────────────┬────────────┘
                           │ Apply Now
              ┌────────────▼────────────┐
              │    AUTO-APPLY ENGINE    │
              │  Playwright + APIs      │
              │  Greenhouse / Lever /   │
              │  HTML Forms / Fallback  │
              └─────────────────────────┘
```

### 6.3 Database Schema (Key Tables)

| Table | Key Columns |
|---|---|
| `listings` | id, title, company, location, remote, description, apply_url, source, date_posted, date_fetched, is_duplicate |
| `scores` | id, listing_id, overall_score, skills_score, experience_score, role_score, reasoning, scored_at |
| `cover_letters` | id, listing_id, content, version, tone, generated_at, edited_by_user |
| `applications` | id, listing_id, status, applied_at, apply_method, notes, follow_up_date |
| `resume` | id, raw_text, skills[], experience[], education, preferred_roles[], updated_at |
| `user_preferences` | id, target_roles[], locations[], remote_pref, min_score_filter, deal_breakers[] |

### 6.4 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/listings` | Fetch all listings with filters, sorting, pagination |
| `GET` | `/api/listings/{id}` | Single listing detail + score + cover letter |
| `POST` | `/api/listings/scrape` | Trigger manual scrape run |
| `GET` | `/api/scores/{listing_id}` | Get match score breakdown |
| `POST` | `/api/cover-letter/generate` | Generate or regenerate cover letter |
| `PUT` | `/api/cover-letter/{id}` | Save edited cover letter |
| `POST` | `/api/apply/{listing_id}` | Trigger auto-apply for a listing |
| `GET` | `/api/applications` | Get all application statuses |
| `PUT` | `/api/applications/{id}` | Update application status / notes |
| `POST` | `/api/resume/upload` | Upload and parse resume |
| `GET` | `/api/resume` | Get parsed resume data |
| `PUT` | `/api/preferences` | Update user preferences |

---

## 7. Project Structure

```
job-autopilot/
├── frontend/                        # Next.js 14
│   ├── app/
│   │   ├── page.tsx                 # Dashboard — all listings
│   │   ├── tracker/                 # Application tracker (Kanban)
│   │   ├── settings/                # Resume upload + preferences
│   │   └── api/                     # Next.js API proxy routes
│   └── components/
│       ├── ListingCard.tsx
│       ├── CoverLetterEditor.tsx
│       ├── FilterBar.tsx
│       └── ScoreBadge.tsx
│
├── backend/                         # FastAPI + Python
│   ├── main.py                      # FastAPI app entry
│   ├── scrapers/
│   │   ├── remotive.py
│   │   ├── weworkremotely.py
│   │   ├── wellfound.py
│   │   ├── hn_hiring.py
│   │   ├── greenhouse.py
│   │   ├── lever.py
│   │   ├── indeed.py
│   │   └── linkedin.py
│   ├── ai/
│   │   ├── matcher.py               # Resume vs job scoring
│   │   └── cover_letter.py          # Cover letter generation
│   ├── applier/
│   │   ├── playwright_apply.py
│   │   ├── greenhouse_apply.py
│   │   └── lever_apply.py
│   ├── db/
│   │   ├── models.py
│   │   └── database.py
│   ├── resume/
│   │   └── parser.py
│   └── scheduler.py                 # APScheduler jobs
│
├── docker-compose.yml
├── .github/
│   └── workflows/                   # CI/CD via GitHub Actions
└── README.md
```

---

## 8. Development Milestones

| Phase | Duration | Deliverables |
|---|---|---|
| Phase 1 — Core Scraping + DB | Week 1–2 | Remotive + WFR scrapers working, SQLite schema, deduplication, APScheduler running daily |
| Phase 2 — Resume Parsing + Scoring | Week 3 | PDF/DOCX parser, AI match scoring via Groq, scores stored in DB |
| Phase 3 — Dashboard MVP | Week 4–5 | Next.js dashboard showing ALL listings, filters, sorting, score badges, pagination |
| Phase 4 — Cover Letter Engine | Week 6 | AI generation via Gemini, editor UI, version history, export |
| Phase 5 — Auto-Apply Engine | Week 7–8 | Greenhouse + Lever API apply, Playwright form-filler, manual fallback |
| Phase 6 — Application Tracker | Week 9 | Kanban board, status updates, notes, CSV export |
| Phase 7 — Polish + Deploy | Week 10 | Docker, Railway/Vercel deployment, README, demo video |

---

## 9. Non-Functional Requirements

| Category | Requirement |
|---|---|
| Performance | Dashboard loads all 500+ listings in under 2 seconds using pagination and API caching |
| Reliability | Scraper failures are isolated — one failed source does not stop others |
| Privacy | All data stored locally or on user's own Supabase instance — no third-party data sharing |
| Security | API keys stored in environment variables, never committed to git |
| Scalability | DB schema supports 10,000+ listings without redesign |
| Maintainability | Each scraper is an independent module — adding a new source requires only one new file |
| Ethics | Auto-apply requires user confirmation by default. ToS-violating platforms clearly labelled. |

---

## 10. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| LinkedIn blocks scraper | High | Medium | Display listings only, no auto-apply. Use public search, rotate user agents. |
| Groq/Gemini API quota exceeded | Medium | Medium | Cache all scores/letters in DB. Fall back to secondary free API. Batch requests. |
| Playwright detected as bot | Medium | High | Add human-like delays, random mouse movements, headless=false option. |
| Job boards change HTML structure | High | Medium | Modular scrapers — update one without breaking others. Monitor with scrape health logs. |
| Resume parsing fails on unusual formats | Low | Low | Fallback to raw text extraction. Allow manual skill entry in profile settings. |

---

## 11. Future Enhancements (v2+)

- **Email integration** — auto-send follow-up emails 1 week after applying
- **Browser extension** — one-click apply on any job board with pre-filled data
- **Salary intelligence** — pull salary data from Levels.fyi / Glassdoor and attach to listings
- **Referral finder** — identify LinkedIn connections at target companies
- **Interview prep mode** — generate likely interview questions per role using AI
- **Analytics dashboard** — apply rate, response rate, score distributions over time
- **Multi-resume support** — different resume variants for different role types

---

## 12. Glossary

| Term | Definition |
|---|---|
| Match Score | AI-generated 0–100 score indicating how well a job listing aligns with the user's resume and preferences |
| Auto-Apply | Automated form submission using Playwright or platform APIs, without user manually filling forms |
| Manual Fallback | When auto-apply is not supported, the system opens the job URL and copies the cover letter to clipboard |
| Deduplication | Process of detecting and skipping listings already stored in the database, identified by job URL |
| Cover Letter Version | Each regeneration of a cover letter saved separately, up to 3 versions per listing |
| Yolo Mode | Optional setting that enables fully automated apply submission without per-application confirmation |
| Greenhouse / Lever | Applicant Tracking Systems used by many tech companies that expose official public job application APIs |

---

*Job Autopilot PRD v1.0 — Confidential — For Internal Use Only*
