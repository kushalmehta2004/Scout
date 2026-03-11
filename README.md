# Scout 🚀

**Scout** is an AI-powered job and internship discovery platform specifically optimized for **junior engineers and entry-level developers**. It automatically scrapes remote-friendly listings, filters out senior/lead roles, and provides match scoring using AI.

## ✨ Features

- **Junior-First Discovery**: Automatically filters out "Senior", "Staff", "Lead", and "Manager" roles. Now optimized for **AI/ML, Data Science, and Software Engineering** roles.
- **Smart Scraping**: Fetches listings from free, high-quality sources (**Indeed, Hacker News, AIJobs.net, Hugging Face, and Y Combinator**).
- **AI Match Scoring**: Analyzes your resume against job descriptions to provide a compatibility score.
- **Resume Parsing**: Upload your resume (PDF/DOCX) to build your profile automatically.
- **Background Scheduler**: Automatically fetches new listings every 12 hours.

---

## 🛠️ Tech Stack

- **Backend**: FastAPI, SQLAlchemy (SQLite), APScheduler, BeautifulSoup/Feedparser.
- **Frontend**: Next.js 14, React, Tailwind CSS, TypeScript.
- **AI**: Integration with Groq/Gemini for match scoring and parsing.

---

## 🚀 Getting Started

### 1. Backend Setup

1. **Python 3.10+** is required.
2. From the project root, navigate to the backend:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```
3. Create the data directory for the database:
   ```bash
   mkdir data
   ```
4. Set up environment variables:
   Copy `.env.example` to `backend/.env` (or project root `.env`) and set your API keys:
   - `GROQ_API_KEY`: Required for AI match scoring.
   - `GOOGLE_API_KEY`: Optional, for Gemini features.

5. **Run the server**:
   ```bash
   python -m uvicorn main:app --reload
   ```
   - API base: [http://localhost:8000](http://localhost:8000)
   - Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### 2. Frontend Setup

1. **Node.js 18+** is required.
2. From the project root, navigate to the frontend:
   ```bash
   cd frontend
   npm install
   ```
3. Set up environment variables:
   Copy `frontend/.env.local.example` to `frontend/.env.local`:
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```
4. **Run the dashboard**:
   ```bash
   npm run dev
   ```
   - Dashboard: [http://localhost:3000](http://localhost:3000)

---

## 📡 API Endpoints

- `GET /api/listings`: List all junior-level jobs/internships.
- `POST /api/listings/scrape`: Manually trigger a new scrape across Indeed, HN, AIJobs, Hugging Face, and YC.
- `POST /api/resume/upload`: Upload and parse your resume.
- `GET /api/scores/{listing_id}`: Get an AI-generated match score for a specific job.

---

## 🤝 Contributing

This project is optimized for entry-level developers. Contributions to improve scraper accuracy or UI/UX are welcome!
