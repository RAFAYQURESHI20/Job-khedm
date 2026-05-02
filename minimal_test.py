"""
minimal_test.py
---------------
Quick smoke tests you can run without a live database or ML model.
Verifies that core modules import correctly and basic logic works.

    python minimal_test.py
"""

import sys
import traceback


def test(name, fn):
    try:
        fn()
        print(f"  ✔  {name}")
        return True
    except Exception as exc:
        print(f"  ✘  {name}")
        traceback.print_exc()
        return False


# ── 1. Config loads ────────────────────────────────────────────────────────────
def _test_config():
    from config import settings
    assert settings.APP_NAME == "JobPulse"
    assert settings.API_V1_PREFIX == "/api/v1"


# ── 2. Models import cleanly ───────────────────────────────────────────────────
def _test_models():
    from models import JobCategory, JobListingCreate, JobType
    listing = JobListingCreate(
        title="Software Engineer",
        company="Acme Corp",
        url="https://example.com/jobs/1",
        source="test",
    )
    assert listing.title == "Software Engineer"


# ── 3. Utility functions ───────────────────────────────────────────────────────
def _test_utils():
    from utils import deduplicate, extract_salary_range, slugify

    assert slugify("Senior Backend Engineer") == "senior-backend-engineer"

    lo, hi = extract_salary_range("$60,000 – $80,000")
    assert lo == 60000 and hi == 80000

    lo2, hi2 = extract_salary_range("PKR 80k–120k/month")
    assert lo2 == 80000 and hi2 == 120000

    listings = [
        {"url": "https://a.com/1", "title": "Dev"},
        {"url": "https://a.com/1", "title": "Dev"},   # duplicate
        {"url": "https://a.com/2", "title": "PM"},
    ]
    assert len(deduplicate(listings)) == 2


# ── 4. BaseScraper is abstract ─────────────────────────────────────────────────
def _test_base_scraper_abstract():
    from base_scraper import BaseScraper
    import inspect
    assert inspect.isabstract(BaseScraper)


# ── Run ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\nJobPulse — Smoke Tests\n" + "─" * 40)
    results = [
        test("Config loads", _test_config),
        test("Models import", _test_models),
        test("Utility functions", _test_utils),
        test("BaseScraper is abstract", _test_base_scraper_abstract),
    ]
    print("─" * 40)
    passed = sum(results)
    total = len(results)
    print(f"{passed}/{total} tests passed.\n")
    sys.exit(0 if passed == total else 1)
