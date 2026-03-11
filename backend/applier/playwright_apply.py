"""
Playwright-based apply: open apply URL, fill common form fields. Optionally submit (default: fill only).
Uses human-like delays. Set PLAYWRIGHT_HEADLESS=false to see the browser (recommended for review).
When auto_submit=False (default), the browser stays open so you can review and click Submit yourself.
"""

import logging
import os
import threading
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# How long to keep the browser open when fill-only (no auto-submit) so user can review and submit
KEEP_BROWSER_OPEN_SECONDS = 30 * 60

# Common selectors for name, email, cover letter, resume upload
NAME_SELECTORS = [
    "input[name*='name']",
    "input[name*='first']",
    "input[id*='name']",
    "input[placeholder*='Name']",
    "input[placeholder*='First']",
]
EMAIL_SELECTORS = [
    "input[name*='email']",
    "input[type='email']",
    "input[id*='email']",
]
COVER_LETTER_SELECTORS = [
    "textarea[name*='cover']",
    "textarea[name*='letter']",
    "textarea[name*='message']",
    "textarea[name*='description']",
    "textarea[id*='cover']",
    "textarea[placeholder*='cover']",
    "textarea[placeholder*='letter']",
]
RESUME_SELECTORS = [
    "input[type='file'][name*='resume']",
    "input[type='file'][name*='cv']",
    "input[type='file'][accept*='pdf']",
    "input[type='file']",
]
SUBMIT_SELECTORS = [
    "button[type='submit']",
    "input[type='submit']",
    "[type='submit']",
]


def _find_and_fill(page, selectors: list, value: str, fill_type: str = "fill") -> bool:
    for sel in selectors:
        try:
            loc = page.locator(sel)
            if loc.count() > 0:
                el = loc.first
                if fill_type == "fill":
                    el.fill(value)
                else:
                    el.set_input_files(value)
                time.sleep(0.2)
                return True
        except Exception:
            continue
    return False


def fill_and_submit(
    apply_url: str,
    cover_letter: str,
    name: str = "",
    email: str = "",
    resume_path: Optional[str] = None,
    headless: Optional[bool] = None,
    auto_submit: bool = False,
) -> bool:
    """
    Open apply_url in Chromium and fill name/email/cover letter/resume.
    If auto_submit=True, also click submit and close. If auto_submit=False (default),
    do NOT click submit; keep the browser open so you can review and click Submit yourself.
    Returns True if we reached the page and filled at least one field.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning("Playwright not installed; run: pip install playwright && playwright install chromium")
        return False

    if headless is None:
        headless = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() in ("1", "true", "yes")
    # When fill-only, show the browser so user can review and submit
    if not auto_submit:
        headless = False

    def _run():
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()
            try:
                page.goto(apply_url, wait_until="domcontentloaded", timeout=15000)
                time.sleep(0.5)

                filled_any = False
                if name and NAME_SELECTORS:
                    if _find_and_fill(page, NAME_SELECTORS, name):
                        filled_any = True
                if email and EMAIL_SELECTORS:
                    if _find_and_fill(page, EMAIL_SELECTORS, email):
                        filled_any = True
                if cover_letter and COVER_LETTER_SELECTORS:
                    if _find_and_fill(page, COVER_LETTER_SELECTORS, cover_letter[:15000]):
                        filled_any = True
                if resume_path and Path(resume_path).exists() and RESUME_SELECTORS:
                    if _find_and_fill(page, RESUME_SELECTORS, resume_path, fill_type="file"):
                        filled_any = True

                time.sleep(0.3)
                if auto_submit:
                    for sel in SUBMIT_SELECTORS:
                        try:
                            loc = page.locator(sel)
                            if loc.count() > 0:
                                loc.first.click()
                                filled_any = True
                                break
                        except Exception:
                            continue
                    time.sleep(1)
                    browser.close()
                else:
                    # Keep browser open so user can review and click Submit
                    logger.info("Form filled; browser will stay open for %s seconds for you to review and submit.", KEEP_BROWSER_OPEN_SECONDS)
                    try:
                        time.sleep(KEEP_BROWSER_OPEN_SECONDS)
                    finally:
                        browser.close()
                return filled_any
            except Exception as e:
                logger.exception("Playwright error: %s", e)
                browser.close()
                return False

    if auto_submit:
        return _run()
    # Fill only: run in background thread so we can return the API response immediately
    result = [None]  # mutable to capture return value
    def thread_target():
        result[0] = _run()

    t = threading.Thread(target=thread_target, daemon=False)
    t.start()
    # Assume success so we can return; user will see the browser
    return True
