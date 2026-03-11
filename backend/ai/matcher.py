"""
AI match scorer: compare resume to job description and return 0-100 scores via Groq.
Returns a dict with overall, skills_score, experience_score, role_score, reasoning.
"""

import json
import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

# Model: use a Groq model that supports good reasoning (see console.groq.com)
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


def _build_resume_summary(raw_text: str, skills: str, experience: str, education: str) -> str:
    """Build a concise summary for the prompt (avoid token overflow)."""
    parts = []
    if raw_text:
        parts.append("Raw resume text (excerpt):\n" + raw_text[:4000].strip())
    if skills and skills != "[]":
        parts.append("Skills (parsed): " + skills[:1500])
    if experience:
        parts.append("Experience:\n" + experience[:2000].strip())
    if education:
        parts.append("Education:\n" + education[:1000].strip())
    return "\n\n".join(parts) if parts else "No resume content provided."


def _parse_score_response(text: str) -> dict[str, Any] | None:
    """Extract JSON from model response; handle markdown code blocks."""
    text = (text or "").strip()
    # Try to find JSON in code block
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        text = m.group(1).strip()
    # Try parse as-is
    try:
        data = json.loads(text)
        return data
    except json.JSONDecodeError:
        pass
    # Try to find first { ... }
    start = text.find("{")
    if start >= 0:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        break
    return None


def score_listing(
    resume_summary: str,
    job_title: str,
    company: str,
    job_description: str,
    api_key: str | None = None,
) -> dict[str, Any]:
    """
    Call Groq to score how well the resume matches the job. Returns dict with:
    overall (0-100), skills_match, experience_match, role_match (0-100), reasoning (str).
    Raises if API key is missing or request fails.
    """
    key = api_key or os.getenv("GROQ_API_KEY")
    if not key:
        raise ValueError("GROQ_API_KEY is not set")

    prompt = f"""You are a recruiter. Score how well this candidate's resume matches the job below.
Give scores from 0 to 100 for: overall match, skills match, experience match, and role match.
Respond with ONLY a JSON object (no markdown, no explanation outside JSON) with these exact keys:
- "overall" (number 0-100)
- "skills_match" (number 0-100)
- "experience_match" (number 0-100)
- "role_match" (number 0-100)
- "reasoning" (string, 1-3 sentences)

CANDIDATE RESUME SUMMARY:
{resume_summary[:6000]}

JOB TITLE: {job_title}
COMPANY: {company}

JOB DESCRIPTION:
{(job_description or "")[:6000]}
"""

    from groq import Groq

    client = Groq(api_key=key)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": "You output only valid JSON with the requested numeric and string fields."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=500,
    )
    content = (response.choices[0].message.content or "").strip()
    data = _parse_score_response(content)
    if not data:
        logger.warning("Groq returned non-JSON response: %s", content[:200])
        return {
            "overall": 50,
            "skills_match": 50,
            "experience_match": 50,
            "role_match": 50,
            "reasoning": "Could not parse score; default 50.",
        }

    def clamp(n: Any) -> int:
        try:
            v = int(n)
            return max(0, min(100, v))
        except (TypeError, ValueError):
            return 50

    return {
        "overall": clamp(data.get("overall", data.get("overall_score", 50))),
        "skills_match": clamp(data.get("skills_match", data.get("skills_score", 50))),
        "experience_match": clamp(data.get("experience_match", data.get("experience_score", 50))),
        "role_match": clamp(data.get("role_match", data.get("role_score", 50))),
        "reasoning": str(data.get("reasoning", ""))[:2000],
    }
