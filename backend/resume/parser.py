"""
Resume parser: extract text from PDF/DOCX and parse into structured fields.
Returns a dict matching the Resume model: raw_text, skills, experience, education, preferred_roles.
"""

import io
import re
from typing import Any

# Lazy imports for optional deps (pdfplumber, python-docx) so the module loads even if not installed


def _extract_text_pdf(content: bytes) -> str:
    import pdfplumber
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        parts = []
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                parts.append(t)
        return "\n\n".join(parts) if parts else ""


def _extract_text_docx(content: bytes) -> str:
    from docx import Document
    doc = Document(io.BytesIO(content))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def _section_split(text: str) -> dict[str, str]:
    """Split raw text into sections by common resume headings. Returns dict of section_name -> content."""
    # Normalize: one line per heading, content follows until next heading
    section_headers = re.compile(
        r"^(?:(?:summary|profile|objective|skills?|experience|work\s+history|education|"
        r"projects|certifications?|preferred\s+roles?|looking\s+for)\s*:?\s*)$",
        re.IGNORECASE | re.MULTILINE,
    )
    sections: dict[str, str] = {}
    lines = text.split("\n")
    current_header: str | None = None
    current_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current_lines:
                current_lines.append("")
            continue
        # Check if this line is a section header (short, often all caps or title case)
        if len(stripped) < 50 and section_headers.match(stripped):
            if current_header is not None:
                sections[current_header] = "\n".join(current_lines).strip()
            # Normalize header key (e.g. "Skills" -> "skills", "Work History" -> "experience")
            key = stripped.rstrip(":").strip().lower()
            if "skill" in key:
                current_header = "skills"
            elif "experience" in key or "work" in key or "employment" in key:
                current_header = "experience"
            elif "education" in key:
                current_header = "education"
            elif "preferred" in key or "looking" in key or "role" in key:
                current_header = "preferred_roles"
            else:
                current_header = key.split()[0] if key else "other"
            current_lines = []
        else:
            current_lines.append(stripped)

    if current_header is not None:
        sections[current_header] = "\n".join(current_lines).strip()

    return sections


def _parse_skills(section: str) -> list[str]:
    """Extract a list of skills from a skills section (comma, bullet, slash, or newline separated)."""
    if not section:
        return []
    # Replace common separators with comma, then split
    normalized = re.sub(r"[\n•\-\*]\s*", ", ", section)
    normalized = re.sub(r"\s*[\/\|]\s*", ", ", normalized)
    parts = [p.strip() for p in re.split(r",\s*", normalized) if p.strip()]
    # Dedupe and filter very short or purely numeric
    seen: set[str] = set()
    result: list[str] = []
    for p in parts:
        if len(p) < 2 or p in seen:
            continue
        if p.isdigit():
            continue
        seen.add(p)
        result.append(p[:200])  # cap length per skill
    return result[:200]  # cap total skills


def _infer_preferred_roles(text: str) -> list[str]:
    """Infer preferred roles from phrases like 'Seeking X role', 'Looking for Y position'."""
    roles: list[str] = []
    # Simple pattern: "Seeking/Looking for ... role/position"
    for m in re.finditer(
        r"(?:seeking|looking\s+for|interested\s+in)\s+[^.]*?(?:role|position|job|title)",
        text,
        re.IGNORECASE,
    ):
        phrase = m.group(0).strip()[:150]
        if phrase and phrase not in roles:
            roles.append(phrase)
    return roles[:20]


def parse_resume(content: bytes, filename: str = "") -> dict[str, Any]:
    """
    Parse a resume file (PDF or DOCX) into structured data.
    Returns dict with keys: raw_text, skills (list), experience (str), education (str), preferred_roles (list).
    """
    raw_text = ""
    fn = (filename or "").lower()

    if fn.endswith(".pdf"):
        raw_text = _extract_text_pdf(content)
    elif fn.endswith(".docx") or fn.endswith(".doc"):
        raw_text = _extract_text_docx(content)
    else:
        # Try PDF first (magic bytes), then DOCX
        if content[:4] == b"%PDF":
            raw_text = _extract_text_pdf(content)
        else:
            raw_text = _extract_text_docx(content)

    raw_text = (raw_text or "").strip()

    sections = _section_split(raw_text)
    skills_list = _parse_skills(sections.get("skills", ""))
    experience = sections.get("experience", "").strip()[:10000]
    education = sections.get("education", "").strip()[:5000]
    preferred = sections.get("preferred_roles", "").strip()
    if not preferred:
        preferred_roles_list = _infer_preferred_roles(raw_text)
    else:
        preferred_roles_list = _parse_skills(preferred)

    return {
        "raw_text": raw_text,
        "skills": skills_list,
        "experience": experience,
        "education": education,
        "preferred_roles": preferred_roles_list,
    }
