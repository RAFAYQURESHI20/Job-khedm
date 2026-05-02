"""
final_scraper.py
----------------
Production multi-source scraper that orchestrates all enabled job board
scrapers, runs ML classification, deduplicates, and upserts to the database.

Usage:
    python final_scraper.py [--sources all] [--dry-run] [--no-classify]
"""

import argparse
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, List

from config import settings
from models import JobListingCreate
from scrapers.parsers.generic_api import GenericAPIParser
from scrapers.parsers.html_parser import HTMLParser
from utils import (
    batch_upsert,
    deduplicate,
    notify_slack,
    setup_logging,
)

logger = logging.getLogger(__name__)

# ── Source registry ──────────────────────────────────────────────────────────
# Each entry maps a logical source name to its scraper class + kwargs.
SOURCES: Dict[str, dict] = {
    "jobboard_a": {
        "cls": GenericAPIParser,
        "kwargs": {
            "base_url": "https://api.jobboard-a.example.com/v2/jobs",
            "page_param": "page",
            "results_key": "data",
        },
    },
    "jobboard_b": {
        "cls": HTMLParser,
        "kwargs": {
            "base_url": "https://www.jobboard-b.example.com/search",
            "listing_selector": "div.job-card",
            "next_page_selector": "a.pagination__next",
        },
    },
    "jobboard_c": {
        "cls": GenericAPIParser,
        "kwargs": {
            "base_url": "https://jobboard-c.example.com/api/listings",
            "page_param": "offset",
            "results_key": "items",
            "use_offset": True,
        },
    },
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def run_scraper(name: str, cfg: dict, dry_run: bool) -> List[dict]:
    """Instantiate and run a single scraper, return raw listing dicts."""
    logger.info("▶ Starting scraper: %s", name)
    try:
        scraper = cfg["cls"](source_name=name, **cfg["kwargs"])
        listings = scraper.run()
        logger.info("✔ %s — %d listings", name, len(listings))
        return listings
    except Exception as exc:
        logger.error("✘ %s failed: %s", name, exc, exc_info=True)
        return []


def classify_listings(listings: List[dict]) -> List[dict]:
    """Run ML classification model over listing titles+descriptions."""
    try:
        from ml.models.classifier import JobClassifier
        clf = JobClassifier(model_path=settings.MODEL_PATH)
        return clf.predict_batch(listings, threshold=settings.CLASSIFICATION_THRESHOLD)
    except ImportError:
        logger.warning("ML classifier not available — skipping classification.")
        return listings
    except Exception as exc:
        logger.error("Classification failed: %s", exc)
        return listings


# ── Main orchestration ───────────────────────────────────────────────────────

def main(args: argparse.Namespace) -> int:
    setup_logging(settings.LOG_LEVEL)
    started_at = datetime.utcnow()

    # Determine which sources to run
    if args.sources == "all":
        active_sources = SOURCES
    else:
        requested = {s.strip() for s in args.sources.split(",")}
        active_sources = {k: v for k, v in SOURCES.items() if k in requested}
        unknown = requested - set(SOURCES)
        if unknown:
            logger.error("Unknown sources: %s", unknown)
            return 1

    # Scrape in parallel (max 3 workers to be polite)
    all_listings: List[dict] = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(run_scraper, name, cfg, args.dry_run): name
            for name, cfg in active_sources.items()
        }
        for future in as_completed(futures):
            all_listings.extend(future.result())

    logger.info("Total raw listings collected: %d", len(all_listings))

    # Deduplicate
    unique = deduplicate(all_listings)
    logger.info("After deduplication: %d unique listings", len(unique))

    # Classify
    if not args.no_classify:
        unique = classify_listings(unique)

    # Build Pydantic objects
    validated = []
    for raw in unique:
        try:
            validated.append(JobListingCreate(**raw))
        except Exception as exc:
            logger.debug("Validation error (skipped): %s — %s", raw.get("url"), exc)

    logger.info("Validated listings ready for DB: %d", len(validated))

    # Upsert
    if not args.dry_run:
        new_count, updated_count = batch_upsert(validated)
        logger.info("DB upsert complete — new: %d, updated: %d", new_count, updated_count)
    else:
        logger.info("[DRY RUN] Would upsert %d listings.", len(validated))
        new_count, updated_count = len(validated), 0

    # Notify
    elapsed = (datetime.utcnow() - started_at).total_seconds()
    notify_slack(
        title="✅ JobPulse daily scrape complete",
        fields={
            "Sources": ", ".join(active_sources.keys()),
            "Total scraped": str(len(all_listings)),
            "Unique": str(len(unique)),
            "New": str(new_count),
            "Updated": str(updated_count),
            "Duration": f"{elapsed:.1f}s",
        },
    )

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="JobPulse production scraper")
    parser.add_argument(
        "--sources", default="all",
        help="Comma-separated source names, or 'all' (default: all)"
    )
    parser.add_argument("--dry-run", action="store_true", help="Skip DB writes")
    parser.add_argument("--no-classify", action="store_true", help="Skip ML classification")
    sys.exit(main(parser.parse_args()))
