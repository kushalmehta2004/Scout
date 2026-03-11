"""
Cover letter generation via Google Gemini. Produces a 3–4 paragraph letter (max 400 words).
"""

import os
from typing import Optional

TONE_OPTIONS = ("Professional", "Conversational", "Technical", "Enthusiastic")
DEFAULT_TONE = "Professional"
MAX_WORDS = 400


def generate_cover_letter(
    resume_summary: str,
    job_title: str,
    company: str,
    job_description: str,
    tone: str = DEFAULT_TONE,
    api_key: Optional[str] = None,
) -> str:
    """
    Call Gemini to generate a cover letter. Returns plain text (3–4 paragraphs, max 400 words).
    Raises ValueError if GEMINI_API_KEY is missing; propagates API errors.
    """
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError("GEMINI_API_KEY is not set")

    tone = tone.strip() or DEFAULT_TONE
    if tone not in TONE_OPTIONS:
        tone = DEFAULT_TONE

    prompt = f"""Write a cover letter for this job application. Use a {tone.lower()} tone.
Requirements:
- Exactly 3 to 4 paragraphs.
- Maximum {MAX_WORDS} words.
- Paragraph 1: Open with a specific hook mentioning the role ("{job_title}") and company ("{company}").
- Paragraph 2: Map your most relevant experience to the job requirements.
- Paragraph 3: Why this company/role (use context from the job description).
- Paragraph 4: Clear call to action and how to reach you.
- No generic filler. Be specific and concise.
- Output only the letter text, no subject line or "Dear Hiring Manager" if you prefer a more modern opening; otherwise a brief greeting is fine.

CANDIDATE RESUME SUMMARY:
{resume_summary[:5000]}

JOB TITLE: {job_title}
COMPANY: {company}

JOB DESCRIPTION:
{(job_description or "")[:6000]}
"""

    import google.generativeai as genai

    genai.configure(api_key=key)
    # Use env override; default to current Flash model (2.5 Flash as of 2025)
    model_name = os.getenv("GEMINI_COVER_MODEL", "gemini-2.5-flash")
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(prompt)
    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("Gemini returned empty cover letter")
    return text[:8000]
