"""
Apply dispatcher: try Playwright to fill and submit apply form; otherwise return manual fallback.
Human-in-the-loop: caller should only invoke after user confirmation (or Yolo Mode).
"""

import logging
import os
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ApplyResult:
    ok: bool
    method: str
    message: str
    apply_url: str
    cover_letter_text: str


def run_apply(
    apply_url: str,
    cover_letter_text: str,
    applicant_name: Optional[str] = None,
    applicant_email: Optional[str] = None,
    resume_path: Optional[str] = None,
) -> ApplyResult:
    """
    Try to apply via Playwright (fill form; user can review and submit in browser).
    On failure or unsupported, return manual fallback (open URL + copy letter).
    """
    name = applicant_name or os.getenv("APPLICATION_NAME", "")
    email = applicant_email or os.getenv("APPLICATION_EMAIL", "")
    resume = resume_path or os.getenv("RESUME_FILE_PATH")

    try:
        from applier.playwright_apply import fill_and_submit
        success = fill_and_submit(
            apply_url=apply_url,
            cover_letter=cover_letter_text,
            name=name,
            email=email,
            resume_path=resume,
        )
        if success:
            return ApplyResult(
                ok=True,
                method="playwright",
                message="Form filled. Review the application in the browser and click Submit when ready.",
                apply_url=apply_url,
                cover_letter_text=cover_letter_text,
            )
    except Exception as e:
        logger.exception("Playwright apply failed: %s", e)

    return ApplyResult(
        ok=False,
        method="manual",
        message="Open the apply link and paste the cover letter from your clipboard.",
        apply_url=apply_url,
        cover_letter_text=cover_letter_text,
    )
